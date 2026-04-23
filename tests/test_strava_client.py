import os
import pytest
from unittest.mock import patch, MagicMock
from strava_client import StravaClient

STRAVA_ENV = {
    'STRAVA_CLIENT_ID': 'cid',
    'STRAVA_CLIENT_SECRET': 'csecret',
    'STRAVA_REFRESH_TOKEN': 'old-refresh-token',
}

RAILWAY_ENV = {
    **STRAVA_ENV,
    'RAILWAY_API_TOKEN': 'railway-api-token',
    'RAILWAY_SERVICE_ID': 'svc-id',
    'RAILWAY_ENVIRONMENT_ID': 'env-id',
    'RAILWAY_PROJECT_ID': 'proj-id',
}


@pytest.fixture()
def client():
    with patch.dict(os.environ, STRAVA_ENV, clear=False):
        return StravaClient()


@pytest.fixture()
def client_with_railway():
    with patch.dict(os.environ, RAILWAY_ENV, clear=False):
        return StravaClient()


# --- token rotation detection ---

def test_no_rotation_when_refresh_token_unchanged(client):
    strava_response = {
        'access_token': 'new-access',
        'refresh_token': 'old-refresh-token',
    }
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(json=lambda: strava_response, raise_for_status=lambda: None)
        with patch.object(client, '_rotate_railway_refresh_token') as mock_rotate:
            client._refresh_access_token()
            mock_rotate.assert_not_called()


def test_rotation_triggered_when_refresh_token_changes(client):
    strava_response = {
        'access_token': 'new-access',
        'refresh_token': 'brand-new-refresh-token',
    }
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(json=lambda: strava_response, raise_for_status=lambda: None)
        with patch.object(client, '_rotate_railway_refresh_token') as mock_rotate:
            client._refresh_access_token()
            mock_rotate.assert_called_once_with('brand-new-refresh-token')


def test_in_memory_token_updated_after_rotation(client):
    strava_response = {
        'access_token': 'new-access',
        'refresh_token': 'brand-new-refresh-token',
    }
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(json=lambda: strava_response, raise_for_status=lambda: None)
        with patch.object(client, '_rotate_railway_refresh_token'):
            client._refresh_access_token()
            assert client.refresh_token == 'brand-new-refresh-token'


def test_no_rotation_when_response_has_no_refresh_token(client):
    strava_response = {'access_token': 'new-access'}
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(json=lambda: strava_response, raise_for_status=lambda: None)
        with patch.object(client, '_rotate_railway_refresh_token') as mock_rotate:
            client._refresh_access_token()
            mock_rotate.assert_not_called()


# --- Railway API call ---

def test_railway_graphql_called_with_correct_payload(client_with_railway):
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            json=lambda: {'data': {'variableUpsert': True}},
            raise_for_status=lambda: None,
        )
        client_with_railway._rotate_railway_refresh_token('rotated-token')

        _, kwargs = mock_post.call_args
        body = kwargs['json']
        assert body['variables']['input']['name'] == 'STRAVA_REFRESH_TOKEN'
        assert body['variables']['input']['value'] == 'rotated-token'
        assert body['variables']['input']['serviceId'] == 'svc-id'
        assert body['variables']['input']['environmentId'] == 'env-id'
        assert body['variables']['input']['projectId'] == 'proj-id'


def test_railway_request_uses_bearer_token(client_with_railway):
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            json=lambda: {'data': {'variableUpsert': True}},
            raise_for_status=lambda: None,
        )
        client_with_railway._rotate_railway_refresh_token('rotated-token')

        _, kwargs = mock_post.call_args
        assert kwargs['headers']['Authorization'] == 'Bearer railway-api-token'


def test_railway_skipped_when_api_token_missing(client):
    with patch('strava_client.requests.post') as mock_post:
        client._rotate_railway_refresh_token('rotated-token')
        mock_post.assert_not_called()


def test_railway_graphql_errors_logged_without_raising(client_with_railway):
    with patch('strava_client.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            json=lambda: {'errors': [{'message': 'unauthorized'}]},
            raise_for_status=lambda: None,
        )
        # must not raise
        client_with_railway._rotate_railway_refresh_token('rotated-token')


def test_railway_network_error_logged_without_raising(client_with_railway):
    with patch('strava_client.requests.post', side_effect=Exception("timeout")):
        client_with_railway._rotate_railway_refresh_token('rotated-token')


# --- config ---

def test_railway_graphql_url_loaded_from_config():
    from config import RAILWAY_GRAPHQL_URL
    assert RAILWAY_GRAPHQL_URL == "https://backboard.railway.app/graphql/v2"


# --- end-to-end: token Strava returns is the exact value sent to Railway ---

def test_new_refresh_token_from_strava_sent_verbatim_to_railway():
    """The token Strava issues must reach Railway unchanged, with no transformation."""
    strava_response = {
        'access_token': 'new-access',
        'refresh_token': 'exactly-this-token',
    }
    railway_response = {'data': {'variableUpsert': True}}

    with patch.dict(os.environ, RAILWAY_ENV, clear=False):
        client = StravaClient()

    with patch('strava_client.requests.post') as mock_post:
        mock_post.side_effect = [
            MagicMock(json=lambda: strava_response, raise_for_status=lambda: None),
            MagicMock(json=lambda: railway_response, raise_for_status=lambda: None),
        ]
        client._refresh_access_token()

    railway_call = mock_post.call_args_list[1]
    sent_value = railway_call[1]['json']['variables']['input']['value']
    assert sent_value == 'exactly-this-token'
