"""Fixed-origin X handle resolution. Authorization remains pinned to numeric IDs."""
import re
import httpx
from .credits import CreditError
from .x_access import x_id

class XLookupUnavailable(CreditError):pass

def handle(value):
    if not isinstance(value,str):raise CreditError('Enter an X handle')
    value=value.strip().removeprefix('@')
    if not re.fullmatch(r'[A-Za-z0-9_]{1,15}',value):raise CreditError('Enter an X handle, without a URL')
    return value

class XLookup:
    def __init__(self,credentials=None,*,fetch=None):self.credentials,self.fetch=credentials,fetch
    def resolve(self,value):
        username=handle(value)
        if not self.credentials and self.fetch is None:raise XLookupUnavailable('X lookup is unavailable. Enter the numeric X ID.')
        try:
            if self.fetch:response=self.fetch(username)
            else:
                token=httpx.post('https://api.x.com/oauth2/token',auth=(self.credentials['clientId'],self.credentials['clientSecret']),
                    data={'grant_type':'client_credentials'},timeout=10,follow_redirects=False)
                if token.status_code!=200:raise XLookupUnavailable('X lookup authentication is unavailable. Use a numeric ID.')
                bearer=token.json()['access_token']
                response=httpx.get('https://api.x.com/2/users/by/username/'+username,
                    headers={'Authorization':'Bearer '+bearer},timeout=10,follow_redirects=False)
            if response.status_code==402:raise XLookupUnavailable('X API credits are required for handle lookup. Use a numeric ID meanwhile.')
            if response.status_code in {404,400}:raise CreditError('X handle was not found')
            if response.status_code!=200:raise XLookupUnavailable('X lookup is temporarily unavailable. Use a numeric ID.')
            data=response.json()['data'];resolved=handle(data['username'])
            if resolved.lower()!=username.lower():raise XLookupUnavailable('X returned a different handle. No access was changed.')
            return {'xId':x_id(data['id']),'handle':resolved}
        except (httpx.HTTPError,KeyError,TypeError,ValueError) as error:
            if isinstance(error,CreditError):raise
            raise XLookupUnavailable('X lookup is temporarily unavailable. Use a numeric ID.') from error
