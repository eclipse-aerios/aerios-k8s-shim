'''
 NGSI-LD REST API Client
'''
import json
import requests
from app import app_config
# from app.m2m_token import get_m2m_token
from app.utils import catch_requests_exceptions#, get_app_logger


class CBClient:
    '''
        Client to query CB
          query entities/{entity_id}
             or
          query entities/
        ... ngsi-ld url params welcome
          patch entity
    '''

    def __init__(self):
        # We only need this in case we query the continuum, NOT when pushing to local broker.
        # self.logger = get_app_logger()
        # token = get_m2m_token("cb")
        # self.logger.info("token: %s", token )
        self.api_url = app_config.CB_URL
        self.api_port = app_config.CB_PORT
        self.url_version = app_config.URL_VERSION
        self.headers = {
            'Content-Type':
            'application/json',
            'Accept':
            'application/json',
            'aeriOS':
            'true',
            # 'Authorization': f'Bearer {token}'
        }

    @catch_requests_exceptions
    def query_entity(self, entity_id, ngsild_params) -> dict:
        '''
            Query entity with ngsi-ld params
            :input
            @param entity_id: the id of the queried entity
            @param ngsi-ld: the query params
            :output
            ngsi-ld object
        '''
        entity_url = f'{self.api_url}:{self.api_port}/{self.url_version}entities/{entity_id}?{ngsild_params}'
        response = requests.get(entity_url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()

    @catch_requests_exceptions
    def query_entities(self, ngsild_params):
        '''
            Query entities with ngsi-ld params
            :input
            @param ngsi-ld: the query params
            :output
            ngsi-ld object
        '''
        entity_url = f"{self.api_url}:{self.api_port}/{self.url_version}entities?{ngsild_params}"
        response = requests.get(entity_url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()

    @catch_requests_exceptions
    def patch_entity(self, entity_id, upd_object: dict, ngsild_params: str = None) -> dict:
        '''
            Upadte entity in aeriOS contiunuum
            :input
            @param entity_id: the id of the queried entity
            @param upd_object: the  json object to update the entity with
            @ngsild_params: string formated ngsild params
            :output
            
        '''

        entity_url = f'{self.api_url}:{self.api_port}/{self.url_version}entities/{entity_id}?{ngsild_params}'
        response = requests.patch(entity_url,
                                  headers=self.headers,
                                  data=json.dumps(upd_object),
                                  timeout=5)
        response.raise_for_status()
        return response.status_code

    @catch_requests_exceptions
    def patch_entity_attr(self, entity_id, attr, upd_object: dict) -> dict:
        '''
            Update entity in aeriOS contiunuum
            :input
            @param entity_id: the id of the queried entity
            @attr: the attribute to be updated
            @param upd_object: the  json object to update the entity with
            :output
            
        '''
        entity_url = f'{self.api_url}:{self.api_port}/{self.url_version}entities/{entity_id}/attrs/{attr}'
        response = requests.patch(entity_url,
                                  headers=self.headers,
                                  data=json.dumps(upd_object),
                                  timeout=15)
        response.raise_for_status()
        return response.status_code

    @catch_requests_exceptions
    def create_entity(self, create_object: dict) -> int:
        '''
            Create entity in aeriOS contiunuum
            :input
            @param create_object: the  json object to update the entity with
            :output
            
        '''
        entity_url = f'{self.api_url}:{self.api_port}/{self.url_version}entities'

        response = requests.post(entity_url,
                                 headers=self.headers,
                                 data=json.dumps(create_object),
                                 timeout=1)
        if response.status_code == 409:
            #FIXME: Service exists, check service components status
            return 409
        response.raise_for_status()
        return response.status_code

    @catch_requests_exceptions
    def delete_entity(self, entity_id, upd_object: dict) -> dict:
        '''
            Upadte entity in aeriOS contiunuum
            :input
            @param entity_id: the id of the queried entity
            @param upd_object: the  json object to update the entity with
            :output
            
        '''
        entity_url = f'{self.api_url}:{self.api_port}/{self.url_version}entities/{entity_id}'
        print(entity_url)
        print(upd_object)
        response = requests.delete(entity_url, headers=self.headers, timeout=1)
        response.raise_for_status()
        return response.status_code
