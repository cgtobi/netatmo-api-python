import math
import time
from typing import Any, Callable, Dict, Optional, Union

import requests
from oauthlib.oauth2 import TokenExpiredError
from requests_oauthlib import OAuth2Session

from .exceptions import NoDevice
from .helpers import _BASE_URL, LOG, postRequest

# Common definitions
_AUTH_REQ = _BASE_URL + "oauth2/token"
_WEBHOOK_URL_ADD = _BASE_URL + "api/addwebhook"
_WEBHOOK_URL_DROP = _BASE_URL + "api/dropwebhook"


class ClientAuth:
    """
    Request authentication and keep access token available through token method. Renew it automatically if necessary
    Args:
        clientId (str): Application clientId delivered by Netatmo on dev.netatmo.com
        clientSecret (str): Application Secret key delivered by Netatmo on dev.netatmo.com
        username (str)
        password (str)
        scope (Optional[str]):
            read_station: to retrieve weather station data (Getstationsdata, Getmeasure)
            read_camera: to retrieve Welcome data (Gethomedata, Getcamerapicture)
            access_camera: to access the camera, the videos and the live stream.
            write_camera: to set home/away status of persons (Setpersonsaway, Setpersonshome)
            read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
            write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
            read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
            access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
            read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
            read_smokedetector: to read the smoke detector status (Gethomedata)
            Several value can be used at the same time, ie: 'read_station read_camera'
    """

    def __init__(
        self, clientId, clientSecret, username, password, scope="read_station"
    ):
        postParams = {
            "grant_type": "password",
            "client_id": clientId,
            "client_secret": clientSecret,
            "username": username,
            "password": password,
            "scope": scope,
        }
        resp = self.postRequest(_AUTH_REQ, postParams)
        self._clientId = clientId
        self._clientSecret = clientSecret
        try:
            self._accessToken = resp["access_token"]
            self.token = resp
        except KeyError:
            LOG.error("Netatmo API returned %s", resp["error"])
            raise NoDevice("Authentication against Netatmo API failed")
        self.refreshToken = resp["refresh_token"]
        self._scope = resp["scope"]
        self.expiration = int(resp["expire_in"] + time.time() - 1800)

    def postRequest(self, url, params=None, timeout=30):
        resp = requests.post(url, data=params, timeout=timeout)
        if not resp.ok:
            LOG.error("The Netatmo API returned %s", resp.status_code)
        try:
            return (
                resp.json()
                if "application/json" in resp.headers.get("content-type")
                else resp.content
            )
        except TypeError:
            LOG.debug("Invalid response %s", resp)
        return None

    def addwebhook(self, webhook_url):
        postParams = {
            "url": webhook_url,
            "app_types": "app_security",
        }
        resp = postRequest(self, _WEBHOOK_URL_ADD, postParams)
        LOG.debug("addwebhook: %s", resp)

    def dropwebhook(self):
        postParams = {"app_types": "app_security"}
        resp = postRequest(self, _WEBHOOK_URL_DROP, postParams)
        LOG.debug("dropwebhook: %s", resp)

    @property
    def accessToken(self):
        if self.expiration < time.time():  # Token should be renewed
            postParams = {
                "grant_type": "refresh_token",
                "refresh_token": self.refreshToken,
                "client_id": self._clientId,
                "client_secret": self._clientSecret,
            }
            resp = postRequest(_AUTH_REQ, postParams)
            self._accessToken = resp["access_token"]
            self.refreshToken = resp["refresh_token"]
            self.expiration = int(resp["expire_in"] + time.time() - 1800)
        return self._accessToken


class NetatmOAuth2:
    """."""

    def __init__(
        self,
        token: Optional[Dict[str, str]] = None,
        client_id: str = None,
        client_secret: str = None,
        token_updater: Optional[Callable[[str], None]] = None,
    ):
        self._api_counter = 0
        self._start_time = time.time()

        self.client_id = client_id
        self.client_secret = client_secret
        self.token_updater = token_updater
        self.scope = (
            "read_station read_camera access_camera read_thermostat "
            "write_thermostat read_presence access_presence read_homecoach "
            "read_smokedetector"
        )

        extra = {"client_id": self.client_id, "client_secret": self.client_secret}

        self._oauth = OAuth2Session(
            client_id=client_id,
            token=token,
            token_updater=token_updater,
            auto_refresh_kwargs=extra,
            scope=self.scope,
        )

        LOG.debug("Access token: %s", self._oauth.token)

    def refresh_tokens(self) -> Dict[str, Union[str, int]]:
        """Refresh and return new tokens."""
        token = self._oauth.refresh_token(f"{_AUTH_REQ}")

        LOG.error("pyatmo NetatmOAuth2 refresh_tokens %s", token)

        if self.token_updater is not None:
            self.token_updater(token)

        return token

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Make a request.
        We don't use the built-in token refresh mechanism of OAuth2 session because
        we want to allow overriding the token refresh logic.
        """
        try:
            return getattr(self._oauth, method)(url, **kwargs)
        except TokenExpiredError:
            self._oauth.token = self.refresh_tokens()

            return getattr(self._oauth, method)(url, **kwargs)

    def postRequest(self, url, params=None, timeout=30):
        self._api_counter += 1
        calls_per_minute = math.ceil(
            (self._api_counter / math.ceil((time.time() - self._start_time) / 60))
        )
        LOG.debug(
            "pyatmo NetatmOAuth2 postRequest COUNT=%s (%s/min.) [%s]",
            self._api_counter,
            calls_per_minute,
            url,
        )

        resp = self._request(method="post", url=url, data=params, timeout=timeout)
        # resp = requests.post(url, data=params, timeout=timeout)

        if not resp.ok:
            LOG.error("The Netatmo API returned %s", resp.status_code)
            LOG.debug("Netato API error: %s", resp)
        try:
            return (
                resp.json()
                if "application/json" in resp.headers.get("content-type")
                else resp.content
            )
        except TypeError:
            LOG.debug("Invalid response %s", resp)
        return None

    @property
    def accessToken(self):
        return self._oauth.token["access_token"]

    @property
    def token(self):
        return self._oauth.token
