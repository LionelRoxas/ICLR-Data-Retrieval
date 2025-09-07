"""
OpenReview API client wrapper
Handles both API v1 (2016-2022) and API v2 (2023-2025)
"""
import openreview
import time
from typing import List, Any, Dict

class OpenReviewClient:
    """Wrapper for OpenReview API with version handling"""
    
    def __init__(self, username: str = None, password: str = None):
        """Initialize both API v1 and v2 clients"""
        # API v2 for newer conferences (2023+)
        self.client_v2 = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net',
            username=username,
            password=password
        )
        
        # API v1 for older conferences (pre-2023)
        self.client_v1 = openreview.Client(
            baseurl='https://api.openreview.net',
            username=username,
            password=password
        )
    
    def get_client(self, year: int):
        """Select appropriate client based on year"""
        return self.client_v2 if year >= 2023 else self.client_v1
    
    def get_submissions(self, year: int) -> List[Any]:
        """
        Get all submissions for a given year
        
        Args:
            year: Conference year (2016-2025)
            
        Returns:
            List of submission objects
        """
        try:
            if year >= 2023:
                # Try API v2 first for 2023+
                print(f"  Attempting API v2 for year {year}...")
                submissions = self._get_v2_submissions(year)
                
                # If v2 fails, try v1 as fallback for ANY year >= 2023
                if not submissions:
                    print(f"  API v2 returned no results, falling back to API v1...")
                    submissions = self._get_v1_submissions(year)
            else:
                # API v1 for pre-2023
                submissions = self._get_v1_submissions(year)
            
            return submissions
            
        except Exception as e:
            print(f"Error fetching submissions for {year}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_v2_submissions(self, year: int) -> List[Any]:
        """
        Get submissions using API v2 for recent conferences
        
        Args:
            year: Conference year (2023+)
            
        Returns:
            List of submission objects with replies attached
        """
        venue_id = f'ICLR.cc/{year}/Conference'
        all_submissions = []
        
        # List of invitation patterns to try for ICLR
        invitation_patterns = [
            f'{venue_id}/-/Submission',         # Primary pattern for 2024-2025
            f'{venue_id}/-/Blind_Submission',   # Alternative pattern
        ]
        
        # Try different invitation patterns
        for invitation in invitation_patterns:
            try:
                print(f"    Trying invitation: {invitation}")
                
                # Try using get_notes with pagination instead of get_all_notes
                offset = 0
                limit = 1000
                batch_submissions = []
                
                while True:
                    try:
                        # Use get_notes instead of get_all_notes for better control
                        notes = self.client_v2.get_notes(
                            invitation=invitation,
                            limit=limit,
                            offset=offset
                        )
                        
                        # Handle different response types
                        if notes is None:
                            break
                        elif hasattr(notes, '__iter__'):
                            # It's iterable
                            notes_list = list(notes)
                            if not notes_list:
                                break
                            batch_submissions.extend(notes_list)
                            print(f"      Retrieved batch: {len(notes_list)} papers (total: {len(batch_submissions)})")
                            
                            if len(notes_list) < limit:
                                break
                            offset += limit
                        else:
                            # Single note or unexpected format
                            break
                            
                        time.sleep(0.5)  # Rate limiting between batches
                        
                    except Exception as e:
                        print(f"      Pagination error: {str(e)[:100]}")
                        break
                
                if batch_submissions:
                    all_submissions = batch_submissions
                    print(f"    ✓ Found {len(all_submissions)} papers with invitation: {invitation}")
                    break
                    
            except Exception as e:
                print(f"    ✗ Failed with {invitation}: {str(e)[:100]}")
                continue
        
        # If no results yet, try content-based query with better error handling
        if not all_submissions:
            try:
                print(f"    Trying content venueid method...")
                offset = 0
                limit = 1000
                batch_submissions = []
                
                while True:
                    try:
                        notes = self.client_v2.get_notes(
                            content={'venueid': venue_id},
                            limit=limit,
                            offset=offset
                        )
                        
                        if notes is None:
                            break
                        elif hasattr(notes, '__iter__'):
                            notes_list = list(notes)
                            if not notes_list:
                                break
                            batch_submissions.extend(notes_list)
                            print(f"      Retrieved batch: {len(notes_list)} papers (total: {len(batch_submissions)})")
                            
                            if len(notes_list) < limit:
                                break
                            offset += limit
                        else:
                            break
                            
                        time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"      Pagination error: {str(e)[:100]}")
                        break
                
                if batch_submissions:
                    all_submissions = batch_submissions
                    print(f"    ✓ Found {len(all_submissions)} papers with venueid")
                    
            except Exception as e:
                print(f"    ✗ venueid method failed: {str(e)[:100]}")
        
        # Process submissions and attach reviews
        if all_submissions:
            print(f"  Processing {len(all_submissions)} papers...")
            processed_submissions = []
            
            for i, note in enumerate(all_submissions):
                if i % 100 == 0 and i > 0:
                    print(f"    Processed {i}/{len(all_submissions)} papers")
                
                try:
                    # Create a wrapper object that mimics v1 structure
                    processed_note = self._create_v2_wrapper(note, year)
                    
                    # Get reviews and replies for this submission
                    try:
                        reviews = self._get_v2_reviews(note.id, year)
                    except:
                        reviews = []
                    
                    # Attach reviews to the processed note
                    if not hasattr(processed_note, 'details'):
                        processed_note.details = {}
                    processed_note.details['replies'] = reviews
                    processed_note.details['directReplies'] = reviews
                    
                    processed_submissions.append(processed_note)
                    
                except Exception as e:
                    print(f"    Warning: Error processing paper {i}: {str(e)[:100]}")
                    try:
                        # Still try to add the note even if processing fails
                        processed_note = self._create_v2_wrapper(note, year)
                        if not hasattr(processed_note, 'details'):
                            processed_note.details = {}
                        processed_note.details['replies'] = []
                        processed_submissions.append(processed_note)
                    except:
                        # Skip this note entirely if we can't process it
                        continue
                
                time.sleep(0.02)  # Smaller delay for rate limiting
            
            print(f"  ✓ Successfully processed {len(processed_submissions)} papers")
            return processed_submissions
        
        print(f"  ✗ No submissions found with API v2")
        return []
    
    def _create_v2_wrapper(self, note: Any, year: int) -> Any:
        """
        Create a wrapper object that normalizes v2 notes to be compatible with v1 structure
        
        Args:
            note: Original v2 note object
            year: Conference year
            
        Returns:
            Wrapped note object with normalized structure
        """
        class NoteWrapper:
            """Wrapper to normalize v2 notes"""
            def __init__(self, v2_note, year):
                # Safe attribute extraction with defaults
                self.id = getattr(v2_note, 'id', '')
                self.forum = getattr(v2_note, 'forum', '')
                self.signatures = getattr(v2_note, 'signatures', [])
                self.invitations = getattr(v2_note, 'invitations', [])
                self.number = getattr(v2_note, 'number', None)
                self.tcdate = getattr(v2_note, 'tcdate', None)
                self.cdate = getattr(v2_note, 'cdate', None)
                
                # Normalize content - v2 has nested structure with 'value' keys
                raw_content = getattr(v2_note, 'content', {})
                self.content = self._normalize_content(raw_content)
                
                # Initialize details
                self.details = {}
            
            def _normalize_content(self, v2_content: Dict) -> Dict:
                """Extract values from v2 nested content structure"""
                if not isinstance(v2_content, dict):
                    return {}
                    
                normalized = {}
                for key, value in v2_content.items():
                    if isinstance(value, dict) and 'value' in value:
                        normalized[key] = value['value']
                    else:
                        normalized[key] = value
                return normalized
        
        return NoteWrapper(note, year)
    
    def _get_v2_reviews(self, forum_id: str, year: int) -> List[Any]:
        """
        Get reviews for a specific submission using v2 API
        
        Args:
            forum_id: The forum ID of the submission
            year: Conference year
            
        Returns:
            List of review objects
        """
        reviews = []
        
        # Try to get all notes in the forum
        try:
            # Use get_notes with forum parameter
            forum_notes = self.client_v2.get_notes(
                forum=forum_id,
                limit=100
            )
            
            if forum_notes and hasattr(forum_notes, '__iter__'):
                for note in forum_notes:
                    # Check if this is a review/meta-review/decision
                    invitations = getattr(note, 'invitations', [])
                    for inv in invitations:
                        if any(keyword in inv for keyword in ['Review', 'Meta_Review', 'Decision', 'Comment']):
                            # Create wrapper for the review
                            wrapped_review = self._create_v2_wrapper(note, year)
                            wrapped_review.invitation = inv
                            reviews.append(wrapped_review)
                            break
            
        except Exception as e:
            # Silently fail - reviews might not be available
            pass
        
        return reviews
    
    def _get_v1_submissions(self, year: int) -> List[Any]:
        """
        Get submissions using API v1 with year-specific formats
        
        Args:
            year: Conference year (2016-2025)
            
        Returns:
            List of submission objects
        """
        # Year-specific invitation formats
        if year == 2016:
            invitations = [
                'ICLR.cc/2016/workshop/-/submission',
                'ICLR.cc/2016/workshop/-/paper'
            ]
        elif year == 2017:
            invitations = [
                'ICLR.cc/2017/conference/-/submission',
                'ICLR.cc/2017/workshop/-/submission'
            ]
        elif year == 2018:
            invitations = [
                'ICLR.cc/2018/Conference/-/Blind_Submission',
                'ICLR.cc/2018/Workshop/-/Submission'
            ]
        elif year >= 2023:
            # For 2023-2025, try these patterns with v1
            invitations = [
                f'ICLR.cc/{year}/Conference/-/Blind_Submission',
                f'ICLR.cc/{year}/Conference/-/Submission',
            ]
        else:
            # 2019-2022 use consistent format
            invitations = [
                f'ICLR.cc/{year}/Conference/-/Blind_Submission'
            ]
        
        all_submissions = []
        
        # Try each invitation format
        for invitation in invitations:
            try:
                print(f"    Trying API v1 invitation: {invitation}")
                notes = self.client_v1.get_all_notes(
                    invitation=invitation,
                    details='directReplies'
                )
                
                if notes:
                    print(f"    ✓ Found {len(notes)} papers with this invitation")
                    all_submissions.extend(notes)
                    # For recent years, stop after finding sufficient results
                    if year >= 2023 and len(all_submissions) > 100:
                        break
                    
            except Exception as e:
                error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
                # Only print if it's not a 404 (expected for non-existent invitations)
                if '404' not in error_msg:
                    print(f"    ✗ Failed with {invitation}: {error_msg}")
                continue
        
        # Try venueid approach if no results
        if not all_submissions:
            try:
                print(f"    Trying content.venueid with API v1")
                notes = self.client_v1.get_all_notes(
                    content={'venueid': f'ICLR.cc/{year}/Conference'},
                    details='directReplies'
                )
                if notes:
                    print(f"    ✓ Found {len(notes)} papers with venueid")
                    all_submissions.extend(notes)
            except Exception as e:
                # Only print non-404 errors
                if '404' not in str(e):
                    print(f"    ✗ venueid failed: {str(e)[:50]}")
        
        # For 2024/2025, also try without '/Conference' suffix
        if not all_submissions and year >= 2024:
            try:
                print(f"    Trying simplified venueid: ICLR.cc/{year}")
                notes = self.client_v1.get_all_notes(
                    content={'venueid': f'ICLR.cc/{year}'},
                    details='directReplies'
                )
                if notes:
                    print(f"    ✓ Found {len(notes)} papers with simplified venueid")
                    all_submissions.extend(notes)
            except:
                pass
        
        # Remove duplicates
        seen = set()
        unique_submissions = []
        for note in all_submissions:
            if note.id not in seen:
                seen.add(note.id)
                unique_submissions.append(note)
        
        if unique_submissions:
            print(f"  ✓ Total unique papers found with API v1: {len(unique_submissions)}")
        
        return unique_submissions
    
    def add_delay(self, seconds: float = 0.1):
        """Add delay for rate limiting"""
        time.sleep(seconds)