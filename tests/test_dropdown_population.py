import pytest
import json
from unittest.mock import MagicMock

class TestDropdownPopulation:
    """Test suite for verifying dropdowns are populated with all available options."""

    def test_portals_dropdown_returns_all_unique_values(self, client, mock_config, mock_db_with_channels):
        """Verify /editor/portals returns all distinct portal names from DB, not just current page."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Setup mock to return specific distinct portals
        # We want to ensure it returns portals even if they are not on the first page of results
        expected_portals = [
            {'portal_name': 'Portal A (Page 1)'}, 
            {'portal_name': 'Portal B (Page 2)'},
            {'portal_name': 'Portal C (Page 3)'}
        ]
        # Clear the side_effect from the fixture so we can set return_value
        mock_cursor.fetchall.side_effect = None
        mock_cursor.fetchall.return_value = expected_portals
        
        # Call the endpoint
        response = client.get('/editor/portals')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure and content
        assert 'portals' in data
        assert len(data['portals']) == 3
        assert 'Portal A (Page 1)' in data['portals']
        assert 'Portal B (Page 2)' in data['portals']
        assert 'Portal C (Page 3)' in data['portals']
        
        # Verify the SQL query used SELECT DISTINCT portal_name
        calls = mock_cursor.execute.call_args_list
        sql_query = str(calls[0]).upper()
        assert 'SELECT DISTINCT PORTAL_NAME' in sql_query
        assert 'FROM CHANNELS' in sql_query
        # Ensure no LIMIT clause (pagination) was used
        assert 'LIMIT' not in sql_query
        assert 'OFFSET' not in sql_query

    def test_genres_dropdown_returns_all_unique_values(self, client, mock_config, mock_db_with_channels):
        """Verify /editor/genres returns all distinct genres from DB."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Setup mock to return specific distinct genres
        expected_genres = [
            {'genre': 'Action'}, 
            {'genre': 'Comedy'}, 
            {'genre': 'Drama'},
            {'genre': 'Sci-Fi'}
        ]
        # Clear the side_effect from the fixture so we can set return_value
        mock_cursor.fetchall.side_effect = None
        mock_cursor.fetchall.return_value = expected_genres
        
        # Call the endpoint
        response = client.get('/editor/genres')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure and content
        assert 'genres' in data
        assert len(data['genres']) == 4
        assert 'Action' in data['genres']
        assert 'Sci-Fi' in data['genres']
        
        # Verify the SQL query used SELECT DISTINCT
        calls = mock_cursor.execute.call_args_list
        sql_query = str(calls[0]).upper()
        assert 'SELECT DISTINCT' in sql_query
        assert 'GENRE' in sql_query
        assert 'FROM CHANNELS' in sql_query
        # Ensure no LIMIT clause was used
        assert 'LIMIT' not in sql_query

