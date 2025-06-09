from fastapi import FastAPI, Query
from starlette.config import Config
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import  RedirectResponse
from authlib.integrations.starlette_client import OAuth
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from providers.proxmox import Proxmox
import datetime

from guacamole import GuacamoleRDP,Guacamole

try:
    locale_strings = Config(env_file='languages/eng')
except:
    print("Could not load language")
try:
    config = Config(env_file='.env')
except:
    print("Config not found")

app = FastAPI(debug=True)
# we need this to save temporary code & state in session
app.add_middleware(GZipMiddleware, minimum_size=1024)
if(config.get('ALLOWED_HOSTS')):
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=str(config.get('ALLOWED_HOSTS')).split(','))
app.add_middleware(SessionMiddleware, secret_key=config.get('SECRET_KEY'))
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

provider = Proxmox(config)
oauth = OAuth(config)
guac = Guacamole(config=config)
oauth.register(
    name='oidc',
    client_kwargs={
        'scope': 'openid email profile',
    },server_metadata_url=config.get('OIDC_METADATA')
)

@app.route('/') 
async def homepage(request ):
    user = request.session.get('user')
    if user:
        
        vm = await provider.get_user_vm(template_name=str(config.get('AUTO_LAUNCH')),user_id=user['email'])

        
        #Pause until the vm is running
        await provider.wait_for_vm_start(vm)

        #Make sure the agent is up
        agent_up = await provider.wait_for_vm_guest(vm)
        
        if agent_up:
            vmip = await provider.get_vm_ip(vm)
            if(vmip != None):
                rdp = GuacamoleRDP(hostname=vmip,ignore_cert=True,username=str(config.get('RDP_USERNAME')),password=str(config.get('RDP_PASSWORD')))
                json = guac.generate_guac_json({"Remote Server":rdp}, user['email'], expires_time=round((datetime.datetime.now() + datetime.timedelta(minutes=3)).timestamp()) )
                ticket = guac.get_guac_token(json)
                if(ticket):
                    resp = templates.TemplateResponse(
                        request=request, name="console.html", context={"user": user, "locale_str":locale_strings, "ticket": ticket, "guac_host":guac.guacamole_url}
                    ) 
                    return resp
            

        else:
            print("Agent was not up")
        
        return templates.TemplateResponse(
                request=request, name="login.html", context={"m": 'No VMs were found', "locale_str":locale_strings}
            )
    else:
        m = ''
        if 'm' in request.query_params:
            m = request.query_params['m']
        return templates.TemplateResponse(
                request=request, name="login.html", context={"m": m, "locale_str":locale_strings}
            )


@app.route('/login')
async def login(request):
    redirect_uri = request.url_for('auth')
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@app.route('/auth')
async def auth(request):
    token = await oauth.oidc.authorize_access_token(request)
    user = token.get('userinfo')
    if user :
        if (any(config.get('ALLOWED_DOMAINS').split(",")) and any(user["email"].endswith(e) for e in str(config.get('ALLOWED_DOMAINS')).split(','))):
            request.session['user'] = user
        else:
            print(str(config.get('ALLOWED_DOMAINS')))
            return RedirectResponse(url=f'/?m=Not allowed domain')        
    return RedirectResponse(url='/') 


@app.route('/logout')
async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')






if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8000)