"""
Process and extract data from OpenReview submissions
"""
from datetime import datetime
from typing import Dict, List, Any

class PaperProcessor:
    """Extract and process paper data from API responses"""
    
    @staticmethod
    def extract_content(content: Dict, is_v2: bool = False) -> Dict:
        """
        Extract content from API response
        API v2 wraps values in {value: ...} objects
        
        Args:
            content: Raw content from API
            is_v2: Whether this is from API v2
            
        Returns:
            Extracted content dictionary
        """
        if is_v2 and isinstance(content, dict):
            extracted = {}
            for key, value in content.items():
                if isinstance(value, dict) and 'value' in value:
                    extracted[key] = value['value']
                else:
                    extracted[key] = value
            return extracted
        return content
    
    @staticmethod
    def extract_reviews(replies: List[Any]) -> List[Dict]:
        """
        Extract official reviews from replies
        
        Args:
            replies: List of reply objects
            
        Returns:
            List of processed review dictionaries
        """
        reviews = []
        
        for reply in replies:
            # Handle both raw dicts and objects
            if hasattr(reply, '__dict__'):
                # Object with attributes
                invitation = getattr(reply, 'invitation', '') or ' '.join(getattr(reply, 'invitations', []))
                content = getattr(reply, 'content', {})
                signatures = getattr(reply, 'signatures', ['Anonymous'])
                tcdate = getattr(reply, 'tcdate', None)
                cdate = getattr(reply, 'cdate', None)
            else:
                # Dictionary
                invitation = reply.get('invitation', '') or ' '.join(reply.get('invitations', []))
                content = reply.get('content', {})
                signatures = reply.get('signatures', ['Anonymous'])
                tcdate = reply.get('tcdate')
                cdate = reply.get('cdate')
            
            # Check if this is an official review
            if 'Official_Review' in invitation or 'Review' in invitation:
                # Extract values from content (handle both v1 and v2 formats)
                if isinstance(content, dict):
                    # Check if it's v2 format (nested with 'value' keys)
                    is_v2_format = any(isinstance(v, dict) and 'value' in v for v in content.values())
                    
                    if is_v2_format:
                        # v2 format - extract from nested structure
                        rating = content.get('rating', {}).get('value') if 'rating' in content else content.get('recommendation', {}).get('value', '')
                        confidence = content.get('confidence', {}).get('value', '')
                        review_text = content.get('review', {}).get('value') if 'review' in content else content.get('comment', {}).get('value', '')
                        strengths = content.get('strengths', {}).get('value', '')
                        weaknesses = content.get('weaknesses', {}).get('value', '')
                        questions = content.get('questions', {}).get('value', '')
                    else:
                        # v1 format - direct access
                        rating = content.get('rating') or content.get('recommendation', '')
                        confidence = content.get('confidence', '')
                        review_text = content.get('review') or content.get('comment', '')
                        strengths = content.get('strengths', '')
                        weaknesses = content.get('weaknesses', '')
                        questions = content.get('questions', '')
                else:
                    rating = ''
                    confidence = ''
                    review_text = ''
                    strengths = ''
                    weaknesses = ''
                    questions = ''
                
                review = {
                    'reviewer_id': signatures[0] if signatures else 'Anonymous',
                    'score': rating,
                    'confidence': confidence,
                    'text': review_text,
                    'date': '',
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'questions': questions
                }
                
                # Format date if available
                if tcdate:
                    review['date'] = datetime.fromtimestamp(
                        tcdate / 1000
                    ).isoformat()
                elif cdate:
                    review['date'] = datetime.fromtimestamp(
                        cdate / 1000
                    ).isoformat()
                
                reviews.append(review)
        
        return reviews
    
    @staticmethod
    def extract_meta_review(replies: List[Any]) -> Dict:
        """
        Extract meta-review from replies
        
        Args:
            replies: List of reply objects
            
        Returns:
            Meta-review dictionary
        """
        for reply in replies:
            # Handle both objects and dicts
            if hasattr(reply, '__dict__'):
                invitation = getattr(reply, 'invitation', '') or ' '.join(getattr(reply, 'invitations', []))
                content = getattr(reply, 'content', {})
            else:
                invitation = reply.get('invitation', '') or ' '.join(reply.get('invitations', []))
                content = reply.get('content', {})
            
            if 'Meta_Review' in invitation or 'MetaReview' in invitation:
                # Check format and extract accordingly
                if isinstance(content, dict):
                    is_v2_format = any(isinstance(v, dict) and 'value' in v for v in content.values())
                    
                    if is_v2_format:
                        metareview_text = content.get('metareview', {}).get('value') if 'metareview' in content else content.get('comment', {}).get('value', '')
                        recommendation = content.get('recommendation', {}).get('value', '')
                    else:
                        metareview_text = content.get('metareview') or content.get('comment', '')
                        recommendation = content.get('recommendation', '')
                else:
                    metareview_text = ''
                    recommendation = ''
                
                return {
                    'text': metareview_text,
                    'decision_rationale': recommendation
                }
        
        return {'text': '', 'decision_rationale': ''}
    
    @staticmethod
    def extract_decision(replies: List[Any]) -> str:
        """
        Extract acceptance decision from replies
        
        Args:
            replies: List of reply objects
            
        Returns:
            Decision string (accept/reject)
        """
        for reply in replies:
            # Handle both objects and dicts
            if hasattr(reply, '__dict__'):
                invitation = getattr(reply, 'invitation', '') or ' '.join(getattr(reply, 'invitations', []))
                content = getattr(reply, 'content', {})
            else:
                invitation = reply.get('invitation', '') or ' '.join(reply.get('invitations', []))
                content = reply.get('content', {})
            
            if 'Decision' in invitation:
                # Extract decision (handle both v1 and v2 formats)
                if isinstance(content, dict):
                    # Check if v2 format
                    if 'decision' in content and isinstance(content['decision'], dict) and 'value' in content['decision']:
                        decision = content['decision']['value'].lower()
                    else:
                        decision = content.get('decision', '').lower()
                else:
                    decision = ''
                
                if 'accept' in decision:
                    return 'accept'
                elif 'reject' in decision:
                    return 'reject'
                elif 'poster' in decision:
                    return 'poster'
                elif 'oral' in decision:
                    return 'oral'
                elif 'spotlight' in decision:
                    return 'spotlight'
        
        # Default to accept for main track
        return 'accept'
    
    @staticmethod
    def build_paper_record(submission: Any, year: int) -> Dict:
        """
        Build complete paper record from submission
        
        Args:
            submission: Submission object from API
            year: Conference year
            
        Returns:
            Complete paper record dictionary
        """
        # Extract content (already normalized if using wrapper)
        content = submission.content if hasattr(submission, 'content') else {}
        
        # Extract replies
        replies = []
        if hasattr(submission, 'details'):
            if isinstance(submission.details, dict):
                replies = submission.details.get('replies', []) or submission.details.get('directReplies', [])
            elif hasattr(submission.details, 'get'):
                replies = submission.details.get('replies', []) or submission.details.get('directReplies', [])
        
        # Extract components
        reviews = PaperProcessor.extract_reviews(replies)
        meta_review = PaperProcessor.extract_meta_review(replies)
        decision = PaperProcessor.extract_decision(replies)
        
        # Build paper record
        paper = {
            'paper_id': submission.id if hasattr(submission, 'id') else '',
            'year': year,
            'title': content.get('title', ''),
            'authors': content.get('authors', []),
            'affiliations': [],  # Would need author profiles
            'abstract': content.get('abstract', ''),
            'url': f'https://openreview.net/forum?id={submission.id}' if hasattr(submission, 'id') else '',
            'pdf_url': '',
            'page_metadata': {
                'venue': f'ICLR.cc/{year}/Conference',
                'keywords': content.get('keywords', []),
                'number': submission.number if hasattr(submission, 'number') else None
            },
            'official_reviews': reviews,
            'meta_review': meta_review,
            'decision': decision,
            'crawl_timestamp': datetime.now().isoformat()
        }
        
        # Add PDF URL if available
        if content.get('pdf'):
            paper['pdf_url'] = f"https://openreview.net{content['pdf']}"
        
        return paper