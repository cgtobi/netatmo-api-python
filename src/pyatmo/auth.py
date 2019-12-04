import logging
import math
import time
from typing import Callable, Dict, Optional, Tuple, Union

import requests
from oauthlib.oauth2 import (
    InvalidClientError,
    LegacyApplicationClient,
    TokenExpiredError,
)
from requests_oauthlib import OAuth2Session

from .helpers import _BASE_URL

LOG = logging.getLogger(__name__)

# Common definitions
_AUTH_REQ = _BASE_URL + "oauth2/token"
_AUTH_URL = _BASE_URL + "oauth2/authorize"
_WEBHOOK_URL_ADD = _BASE_URL + "api/addwebhook"
_WEBHOOK_URL_DROP = _BASE_URL + "api/dropwebhook"


# Possible scops
ALL_SCOPES = [
    "read_station",
    "read_camera",
    "access_camera",
    "write_camera",
    "read_presence",
    "access_presence",
    "read_homecoach",
    "read_smokedetector",
    "read_thermostat",
    "write_thermostat",
]


class NetatmOAuth2:
    """Implementation of of the oauth ."""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: Optional[str] = None,
        token: Optional[Dict[str, str]] = None,
        token_updater: Optional[Callable[[str], None]] = None,
        scope: str = "read_station",
    ):
        self._api_counter = 0
        self._start_time = time.time()

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_updater = token_updater
        self.scope = " ".join(ALL_SCOPES)

        self.extra = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        self._oauth = OAuth2Session(
            client_id=self.client_id,
            token=token,
            token_updater=self.token_updater,
            redirect_uri=self.redirect_uri,
            auto_refresh_kwargs=self.extra,
            auto_refresh_url=_AUTH_REQ,
            scope=self.scope,
        )

    def refresh_tokens(self) -> Dict[str, Union[str, int]]:
        """Refresh and return new tokens."""
        LOG.debug("Refreshing token")
        token = self._oauth.refresh_token(f"{_AUTH_REQ}", include_client_id=True)

        LOG.debug("refreshed token %s", token)
        print(f"refreshed token {token}")

        if self.token_updater is not None:
            self.token_updater(token)

        return token

    def postRequest(self, url, params={}, timeout=30):
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

        print(url, self._oauth.token["expires_at"])
        if "http://" in url:
            resp = requests.post(url, data=params, timeout=timeout)
        else:
            try:
                resp = self._oauth.post(url=url, data=params, timeout=timeout)
            except (InvalidClientError, TokenExpiredError):
                self.refresh_tokens()
                resp = self._oauth.post(url=url, data=params, timeout=timeout)

        if not resp.ok:
            LOG.error("The Netatmo API returned %s", resp.status_code)
            LOG.debug("Netato API error: %s", resp.content)
        try:
            return (
                resp.json()
                if "application/json" in resp.headers.get("content-type")
                else resp.content
            )
        except TypeError:
            LOG.debug("Invalid response %s", resp)
        return None

    def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        return self._oauth.authorization_url(_AUTH_URL, state)

    def request_token(
        self, authorization_response: Optional[str] = None, code: Optional[str] = None
    ) -> Dict[str, str]:
        """Generic method for fetching a Netatmo access token.
        :param authorization_response: Authorization response URL, the callback
                                       URL of the request back to you.
        :param code: Authorization code
        :return: A token dict
        """
        return self._oauth.fetch_token(
            _AUTH_REQ,
            authorization_response=authorization_response,
            code=code,
            client_secret=self.client_secret,
        )

    def addwebhook(self, webhook_url):
        print(webhook_url)
        print(_WEBHOOK_URL_ADD)
        postParams = {
            "url": webhook_url,
        }
        resp = self.postRequest(_WEBHOOK_URL_ADD, postParams)
        print(resp)
        LOG.debug("addwebhook: %s", resp)

    def dropwebhook(self):
        print(_WEBHOOK_URL_ADD)
        postParams = {"app_types": "app_security"}
        resp = self.postRequest(_WEBHOOK_URL_DROP, postParams)
        print(resp)
        LOG.debug("dropwebhook: %s", resp)


class ClientAuth(NetatmOAuth2):
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
            access_camera: to access the camera, the videos and the live stream
            write_camera: to set home/away status of persons (Setpersonsaway, Setpersonshome)
            read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
            write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
            read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
            access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
            read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
            read_smokedetector: to retrieve the smoke detector status (Gethomedata)
            Several value can be used at the same time, ie: 'read_station read_camera'
    """

    def __init__(
        self, clientId, clientSecret, username, password, scope="read_station"
    ):
        self._clientId = clientId
        self._clientSecret = clientSecret

        self._oauth = OAuth2Session(client=LegacyApplicationClient(client_id=clientId))
        self._oauth.fetch_token(
            token_url=_AUTH_REQ,
            username=username,
            password=password,
            client_id=clientId,
            client_secret=clientSecret,
            scope=scope,
        )
