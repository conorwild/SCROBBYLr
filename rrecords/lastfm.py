from pylast import (
    LastFMNetwork, SessionKeyGenerator, _Request, _extract
)
import xmltodict


class LastFMNetwork(LastFMNetwork):

    def get_autheniticated_user_info(self):
        req = _Request(self, "user.getInfo")
        req.sign_it()
        doc = req.execute()
        return xmltodict.parse(doc.toxml())['lfm']['user']



class SessionKeyGenerator(SessionKeyGenerator):

    def handshake_web_auth_url(self, callback_url):
        """
        An extra auth URL builder to supply a callback URL for the handshake
        process. Don't seem to need the token for this?
        """
        token = self._get_web_auth_token()
        url = (
            f"{self.network.homepage}/api/auth/"
            f"?api_key={self.network.api_key}"
            f"&cb={callback_url}"
        )
        self.web_auth_tokens[url] = token
        return url

    def handshake_get_session_key(self, auth_token):
        params = {'token': auth_token}
        request = _Request(self.network, "auth.getSession", params)
        request.sign_it()
        response = request.execute()
        return _extract(response, "key")
