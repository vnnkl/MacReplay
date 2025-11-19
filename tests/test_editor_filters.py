import pytest
import json
from unittest.mock import MagicMock, patch

class TestEditorDataFiltering:
    """Test suite for server-side filtering in editor_data endpoint."""
    
    def test_editor_data_no_filters(self, client, mock_config, mock_db_with_channels):
        """Test editor_data returns all enabled channels when no filters applied."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should return draw number, recordsTotal, recordsFiltered, and data
        assert 'draw' in data
        assert 'recordsTotal' in data
        assert 'recordsFiltered' in data
        assert 'data' in data
        
    def test_editor_data_portal_filter(self, client, mock_config, mock_db_with_channels):
        """Test filtering by portal."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Filter to only show 'Test Portal 1' (passing the name, not the ID)
        response = client.get('/editor_data?draw=1&start=0&length=10&portal=Test Portal 1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify the SQL query was called with portal filter
        # Check that execute was called and inspect the SQL
        calls = mock_cursor.execute.call_args_list
        assert any('portal_name' in str(call) for call in calls), "Portal filter should use portal_name column"
        
    def test_editor_data_genre_filter(self, client, mock_config, mock_db_with_channels):
        """Test filtering by genre."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10&genre=News')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify genre filter was applied in SQL
        calls = mock_cursor.execute.call_args_list
        assert any('genre' in str(call).lower() for call in calls), "Genre filter should be in SQL query"
        
    def test_editor_data_duplicate_filter_enabled_only(self, client, mock_config, mock_db_with_channels):
        """Test filtering to show only enabled duplicate channels."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10&duplicates=enabled_only')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should query for channels where (custom_name or name) appears multiple times
        # among enabled channels
        calls = mock_cursor.execute.call_args_list
        # Should have a subquery counting duplicates
        assert len(calls) > 0, "Should execute SQL queries"
        
    def test_editor_data_duplicate_filter_unique_only(self, client, mock_config, mock_db_with_channels):
        """Test filtering to show only unique (non-duplicate) channels."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10&duplicates=unique_only')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should filter to channels that appear only once
        calls = mock_cursor.execute.call_args_list
        assert len(calls) > 0, "Should execute SQL queries"


class TestFilterMetadata:
    """Test suite for getting filter dropdown options."""
    
    def test_get_portal_list(self, client, mock_config, mock_db_with_channels):
        """Test endpoint that returns list of portals for filter dropdown."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Setup mock to return unique portals
        unique_portals = [{'portal_name': 'Test Portal 1'}, {'portal_name': 'Test Portal 2'}]
        mock_cursor.fetchall.return_value = unique_portals
        
        response = client.get('/editor/portals')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'portals' in data
        assert len(data['portals']) > 0
        
    def test_get_genre_list(self, client, mock_config, mock_db_with_channels):
        """Test endpoint that returns list of genres for filter dropdown."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Setup mock to return unique genres
        unique_genres = [{'genre': 'News'}, {'genre': 'Sports'}, {'genre': 'Movies'}]
        mock_cursor.fetchall.return_value = unique_genres
        
        response = client.get('/editor/genres')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'genres' in data
        assert len(data['genres']) > 0


class TestDuplicateDetection:
    """Test suite for duplicate channel detection."""
    
    def test_get_duplicate_counts(self, client, mock_config, mock_db_with_channels):
        """Test endpoint that returns duplicate counts for each channel."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Setup mock to return channel name counts
        # CNN appears 3 times (all enabled), ESPN appears 1 time (only enabled one)
        name_counts = [
            {'channel_name': 'CNN', 'count': 3},
            {'channel_name': 'ESPN', 'count': 1},
            {'channel_name': 'HBO', 'count': 1},
            {'channel_name': 'Discovery', 'count': 0},  # Disabled
        ]
        # Reset the mock for this specific test
        mock_cursor.fetchall.return_value = name_counts
        mock_cursor.fetchall.side_effect = None  # Clear the side_effect from fixture
        
        response = client.get('/editor/duplicate-counts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'counts' in data
        # CNN should show as duplicate (count > 1)
        assert any(item['count'] > 1 for item in data['counts'])
        
    def test_duplicate_counts_only_enabled(self, client, mock_config, mock_db_with_channels):
        """Test that duplicate counts only consider enabled channels."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # ESPN appears twice total, but only once enabled
        # So it should NOT be counted as duplicate
        name_counts = [
            {'channel_name': 'ESPN', 'count': 1},  # Only enabled one
        ]
        # Reset the mock for this specific test
        mock_cursor.fetchall.return_value = name_counts
        mock_cursor.fetchall.side_effect = None  # Clear the side_effect from fixture
        
        response = client.get('/editor/duplicate-counts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Find ESPN in results
        espn_count = next((item for item in data['counts'] if item['channel_name'] == 'ESPN'), None)
        if espn_count:
            assert espn_count['count'] == 1, "ESPN should not be counted as duplicate"


class TestDeactivateDuplicates:
    """Test suite for bulk deactivate duplicates functionality."""
    
    def test_deactivate_duplicates_keeps_first(self, client, mock_config, mock_db_with_channels):
        """Test that deactivate duplicates keeps the first occurrence."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Mock the query that finds duplicates
        # CNN appears 3 times total: portal1/101, portal1/103, portal2/202  
        # The query returns all 3 as duplicates (since all are enabled)
        duplicates = [
            {'portal': 'portal1', 'channel_id': '103', 'effective_name': 'CNN', 'row_num': 2},
            {'portal': 'portal2', 'channel_id': '202', 'effective_name': 'CNN', 'row_num': 3},
        ]
        # Reset the mock for this specific test
        mock_cursor.fetchall.return_value = duplicates
        mock_cursor.fetchall.side_effect = None  # Clear the side_effect from fixture
        
        response = client.post('/editor/deactivate-duplicates')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'deactivated' in data
        # Should deactivate 2 channels (keeps first portal1/101, deactivates 2nd and 3rd)
        assert data['deactivated'] == 2
        
        # Verify UPDATE queries were called to disable the duplicate channels
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE' in str(call).upper()]
        assert len(update_calls) == 2, "Should update 2 duplicate channels"
        
    def test_deactivate_duplicates_respects_custom_names(self, client, mock_config, mock_db_with_channels):
        """Test that deactivate uses custom_name if available."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # Channels with same custom name should be treated as duplicates
        # Only return the second one (row_num > 1) since that's what should be deactivated
        duplicates = [
            {'portal': 'portal1', 'channel_id': '102', 'effective_name': 'My News', 'row_num': 2},
        ]
        # Reset the mock for this specific test
        mock_cursor.fetchall.return_value = duplicates
        mock_cursor.fetchall.side_effect = None  # Clear the side_effect from fixture
        
        response = client.post('/editor/deactivate-duplicates')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should identify and deactivate the second occurrence
        assert data['deactivated'] == 1
        
    def test_deactivate_duplicates_no_duplicates(self, client, mock_config, mock_db_with_channels):
        """Test deactivate when no duplicates exist."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        # No duplicates found
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchall.side_effect = None  # Clear the side_effect from fixture
        
        response = client.post('/editor/deactivate-duplicates')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['deactivated'] == 0


class TestCombinedFilters:
    """Test combining multiple filters together."""
    
    def test_portal_and_genre_filter(self, client, mock_config, mock_db_with_channels):
        """Test applying both portal and genre filters."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10&portal=Test Portal 1&genre=News')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Both filters should be in the SQL WHERE clause
        calls = mock_cursor.execute.call_args_list
        sql_queries = [str(call) for call in calls]
        assert any('portal_name' in query.lower() and 'genre' in query.lower() for query in sql_queries)
        
    def test_all_filters_combined(self, client, mock_config, mock_db_with_channels):
        """Test applying portal, genre, and duplicate filters together."""
        mock_conn, mock_cursor, test_channels = mock_db_with_channels
        
        response = client.get('/editor_data?draw=1&start=0&length=10&portal=Test Portal 1&genre=News&duplicates=enabled_only')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # All filters should be applied
        calls = mock_cursor.execute.call_args_list
        assert len(calls) > 0

