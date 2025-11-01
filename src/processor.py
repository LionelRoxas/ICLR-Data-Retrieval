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
                # Object with attributes (API v1)
                invitations = getattr(reply, 'invitations', [])
                invitation = getattr(reply, 'invitation', '') or ' '.join(str(inv) for inv in invitations)
                content = getattr(reply, 'content', {})
                signatures = getattr(reply, 'signatures', ['Anonymous'])
                tcdate = getattr(reply, 'tcdate', None)
                cdate = getattr(reply, 'cdate', None)
            else:
                # Dictionary (API v2 - 2024+)
                invitations = reply.get('invitations', [])
                # Safely handle invitations that might be dicts, strings, or mixed
                invitation_parts = []
                for inv in invitations:
                    if isinstance(inv, dict):
                        invitation_parts.append(inv.get('id', inv.get('name', str(inv))))
                    elif isinstance(inv, str):
                        invitation_parts.append(inv)
                    else:
                        invitation_parts.append(str(inv))
                
                invitation = ' '.join(invitation_parts) if invitation_parts else reply.get('invitation', '')
                
                content = reply.get('content', {})
                signatures = reply.get('signatures', ['Anonymous'])
                tcdate = reply.get('tcdate')
                cdate = reply.get('cdate')
            
            # Convert invitation to lowercase for matching
            invitation_lower = invitation.lower()
            
            # Check if this is a review (not meta-review or decision)
            is_review = any(pattern in invitation_lower for pattern in [
                'official_review',
                'official_comment',
                '/review',
                '/comment',
                'public_comment'
            ])
            
            # Exclude meta-reviews, decisions, and other non-review content
            is_excluded = any(pattern in invitation_lower for pattern in [
                'meta_review',
                'metareview', 
                'decision',
                'accept',
                'reject',
                'withdraw',
                'desk_reject',
                'author_rebuttal',
                'response',
                'authors'
            ])

            # Also check the content to filter out author responses
            if is_review and not is_excluded:
                # Additional check: if it's from authors, skip it
                if signatures and any('Author' in str(sig) for sig in signatures):
                    continue  # Skip author responses
                
                # Check content for author response patterns
                if isinstance(content, dict):
                    # Safely extract text from fields that might be dicts or strings
                    text_parts = []
                    for field in ['summary_of_the_review', 'summary_of_the_paper', 'comment', 'review']:
                        field_value = content.get(field, '')
                        if isinstance(field_value, dict):
                            # If it's a dict, try to get the 'value' key
                            text_parts.append(str(field_value.get('value', '')))
                        else:
                            # If it's already a string or other type
                            text_parts.append(str(field_value))
                    
                    text_to_check = ' '.join(text_parts)[:200].lower()
                    
                    if any(phrase in text_to_check for phrase in [
                        'thank all reviewers',
                        'we thank',
                        'we appreciate',
                        'we have revised',
                        'we have updated'
                    ]):
                        continue 
            
            # For 2017 specifically
            if not is_review and '2017' in invitation:
                is_review = 'paper' in invitation_lower and any(
                    pattern in invitation_lower for pattern in ['review', 'comment']
                )
            
            if is_review and not is_excluded:
                # Extract values from content
                if isinstance(content, dict):
                    # Check if it's v2 format (nested with 'value' keys)
                    is_v2_format = any(
                        isinstance(v, dict) and 'value' in v 
                        for v in content.values()
                    )
                    
                    if is_v2_format:
                        # v2 format - extract from nested structure
                        rating = (
                            content.get('rating', {}).get('value') if 'rating' in content 
                            else content.get('recommendation', {}).get('value', '')
                        )
                        confidence = content.get('confidence', {}).get('value', '')
                        review_text = (
                            content.get('review', {}).get('value') if 'review' in content 
                            else content.get('comment', {}).get('value') if 'comment' in content
                            else content.get('text', {}).get('value', '')  # Also check 'text' field
                        )
                        strengths = content.get('strengths', {}).get('value', '')
                        weaknesses = content.get('weaknesses', {}).get('value', '')
                        questions = content.get('questions', {}).get('value', '')
                        summary = content.get('summary', {}).get('value', '')
                    else:
                        # v1 format - direct access
                        # Try all possible field names for rating
                        rating = (
                            content.get('rating') or 
                            content.get('recommendation') or
                            content.get('score', '')
                        )
                        
                        confidence = content.get('confidence', '')
                        
                        # Try all possible field names for review text
                        review_text = (
                            content.get('review') or 
                            content.get('text') or  # Also check 'text' field
                            content.get('comment') or 
                            content.get('main_review') or
                            content.get('summary_of_contributions') or
                            content.get('summary_of_the_review') or  # 2023 style
                            content.get('summary_of_the_paper', '')  # 2023 style
                        )
                        
                        # Handle various strength/weakness formats
                        if 'strength_and_weaknesses' in content:
                            # Combined field (2023 and possibly others)
                            combined = content['strength_and_weaknesses']
                            strengths = combined
                            weaknesses = ''  # Combined with strengths
                        elif 'strengths_and_weaknesses' in content:
                            # Alternative spelling
                            combined = content['strengths_and_weaknesses']
                            strengths = combined
                            weaknesses = ''
                        else:
                            # Separate fields (most years)
                            strengths = content.get('strengths', '')
                            weaknesses = content.get('weaknesses', '')
                        
                        # Try various question/comment field names
                        questions = (
                            content.get('questions') or
                            content.get('clarity,_quality,_novelty_and_reproducibility') or  # 2023
                            content.get('additional_comments') or
                            content.get('comments', '')
                        )
                        
                        # Try various summary field names
                        summary = (
                            content.get('summary') or
                            content.get('summary_of_the_paper') or  # 2023
                            content.get('summary_of_the_review') or  # 2023
                            content.get('brief_summary', '')
                        )
                    
                    # If review_text is empty but we have other components, combine them
                    # This is especially important for 2024 where text field is often empty
                    if not review_text and (summary or strengths or weaknesses or questions):
                        parts = []
                        
                        # Add summary first as it's usually the overview
                        if summary:
                            parts.append(f"**Summary:**\n{summary}")
                        
                        # Add strengths
                        if strengths:
                            parts.append(f"**Strengths:**\n{strengths}")
                        
                        # Add weaknesses
                        if weaknesses:
                            parts.append(f"**Weaknesses:**\n{weaknesses}")
                        
                        # Add questions/additional comments
                        if questions:
                            parts.append(f"**Questions/Comments:**\n{questions}")
                        
                        # Add any other fields that might contain review content
                        for field_name in ['detailed_comments', 'general_comments', 
                                        'technical_quality', 'clarity', 'originality', 
                                        'significance', 'pros', 'cons']:
                            if field_name in content:
                                field_value = content[field_name]
                                # Handle if the field is also a dict with 'value' (v2 format)
                                if isinstance(field_value, dict) and 'value' in field_value:
                                    field_value = field_value['value']
                                if field_value:
                                    field_label = field_name.replace('_', ' ').title()
                                    parts.append(f"**{field_label}:**\n{field_value}")
                        
                        review_text = '\n\n'.join(parts)
                    
                else:
                    rating = ''
                    confidence = ''
                    review_text = ''
                    strengths = ''
                    weaknesses = ''
                    questions = ''
                    summary = ''
                
                # Only add if there's actual review content
                if review_text or summary or strengths or weaknesses:
                    review = {
                        'reviewer_id': signatures[0] if signatures else 'Anonymous',
                        'score': rating,
                        'confidence': confidence,
                        'text': review_text,  # This now contains the combined text
                        'date': '',
                        'strengths': strengths,  # Keep individual fields too
                        'weaknesses': weaknesses,
                        'questions': questions,
                        'summary': summary
                    }

                    # Filter out author responses before adding
                    if 'Authors' in review['reviewer_id']:
                        continue  # Skip author responses
                    
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
    def extract_meta_review(replies: List[Any], year: int = None) -> Dict:
        """
        Extract meta-review from replies
        
        Args:
            replies: List of reply objects
            year: Conference year (optional, for year-specific handling)
            
        Returns:
            Meta-review dictionary
        """
        for reply in replies:
            # Handle both objects and dicts
            if hasattr(reply, '__dict__'):
                # Object with attributes (API v1)
                invitations = getattr(reply, 'invitations', [])
                invitation = getattr(reply, 'invitation', '') or ' '.join(str(inv) for inv in invitations)
                content = getattr(reply, 'content', {})
            else:
                # Dictionary (API v2 - 2024+)
                invitations = reply.get('invitations', [])
                # Safely handle invitations that might be dicts, strings, or mixed
                invitation_parts = []
                for inv in invitations:
                    if isinstance(inv, dict):
                        invitation_parts.append(inv.get('id', inv.get('name', str(inv))))
                    elif isinstance(inv, str):
                        invitation_parts.append(inv)
                    else:
                        invitation_parts.append(str(inv))
                
                invitation = ' '.join(invitation_parts) if invitation_parts else reply.get('invitation', '')
                
                content = reply.get('content', {})
            
            # Convert to lowercase for matching
            invitation_lower = invitation.lower()
            
            # Check for meta-review patterns
            is_meta_review = any(pattern in invitation_lower for pattern in [
                'meta_review', 
                'metareview', 
                'meta-review',
                'decision',
                'accept',
                'reject',
                'poster',
                'spotlight',
                'oral'
            ])
            
            if is_meta_review:
                # Check format and extract accordingly
                if isinstance(content, dict):
                    is_v2_format = any(isinstance(v, dict) and 'value' in v for v in content.values())
                    
                    if is_v2_format:
                        # v2 format - nested structure
                        metareview_text = (
                            content.get('metareview', {}).get('value') or
                            content.get('meta_review', {}).get('value') or
                            content.get('comment', {}).get('value') or
                            content.get('decision', {}).get('value') or
                            content.get('justification', {}).get('value', '')
                        )
                        recommendation = (
                            content.get('recommendation', {}).get('value') or
                            content.get('decision', {}).get('value', '')
                        )
                    else:
                        # v1 format - direct access
                        # Try MANY field names used across different years
                        metareview_text = (
                            content.get('metareview') or 
                            content.get('meta_review') or
                            content.get('comment') or
                            content.get('decision_comment') or
                            content.get('justification') or
                            content.get('acceptance_decision') or
                            content.get('program_chair_comment') or
                            content.get('area_chair_comment', '')
                        )
                        
                        # For 2023, check the special field names
                        if not metareview_text or len(metareview_text) < 50:
                            # Try 2023-specific fields
                            meta_summary = content.get('metareview:_summary,_strengths_and_weaknesses', '')
                            higher_just = content.get('justification_for_why_not_higher_score', '')
                            lower_just = content.get('justification_for_why_not_lower_score', '')
                            
                            # Combine available 2023 fields
                            parts = []
                            if meta_summary:
                                parts.append(meta_summary)
                            if higher_just:
                                parts.append(f"Why not higher: {higher_just}")
                            if lower_just:
                                parts.append(f"Why not lower: {lower_just}")
                            
                            if parts:
                                metareview_text = '\n\n'.join(parts)
                        
                        recommendation = (
                            content.get('recommendation') or
                            content.get('decision', '')
                        )
                else:
                    metareview_text = ''
                    recommendation = ''
                
                # Return if we found content
                if metareview_text or recommendation:
                    return {
                        'text': metareview_text,
                        'decision_rationale': recommendation
                    }
        
        # No meta-review found
        return {'text': '', 'decision_rationale': ''}
          
    @staticmethod
    def extract_decision(replies: List[Any]) -> str:
        """
        Extract acceptance decision from replies
        
        Args:
            replies: List of reply objects
            
        Returns:
            Decision string (accept/reject/workshop_paper)
        """
        # Check if any reply indicates this is a workshop paper
        is_workshop = False
        
        for reply in replies:
            # Handle both objects and dicts
            if hasattr(reply, '__dict__'):
                invitations = getattr(reply, 'invitations', [])
                invitation = getattr(reply, 'invitation', '') or ' '.join(str(inv) for inv in invitations)
                content = getattr(reply, 'content', {})
            else:
                # Dictionary (API v2 - 2024+)
                invitations = reply.get('invitations', [])
                # Safely handle invitations that might be dicts, strings, or mixed
                invitation_parts = []
                for inv in invitations:
                    if isinstance(inv, dict):
                        invitation_parts.append(inv.get('id', inv.get('name', str(inv))))
                    elif isinstance(inv, str):
                        invitation_parts.append(inv)
                    else:
                        invitation_parts.append(str(inv))
                
                invitation = ' '.join(invitation_parts) if invitation_parts else reply.get('invitation', '')
                
                content = reply.get('content', {})
            
            # Check if this is a workshop paper
            if 'workshop' in invitation.lower():
                is_workshop = True
            
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
        
        # If we found evidence this is a workshop paper
        if is_workshop:
            return 'workshop_paper'
        
        # Default to accept for main track
        return None
    
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
        try:
            # Extract content (already normalized if using wrapper)
            content = submission.content if hasattr(submission, 'content') else {}
            
            # Extract replies
            replies = []
            if hasattr(submission, 'details'):
                if isinstance(submission.details, dict):
                    replies = submission.details.get('replies', []) or submission.details.get('directReplies', [])
                elif hasattr(submission.details, 'get'):
                    replies = submission.details.get('replies', []) or submission.details.get('directReplies', [])
            
            # Extract components with better error handling
            try:
                reviews = PaperProcessor.extract_reviews(replies)
            except Exception as e:
                print(f"    DEBUG: Error in extract_reviews: {e}")
                print(f"    DEBUG: Reply type: {type(replies[0]) if replies else 'no replies'}")
                if replies and isinstance(replies[0], dict):
                    print(f"    DEBUG: First reply keys: {list(replies[0].keys())[:10]}")
                raise
                
            try:
                meta_review = PaperProcessor.extract_meta_review(replies, year)
            except Exception as e:
                print(f"    DEBUG: Error in extract_meta_review: {e}")
                raise
                
            try:
                decision = PaperProcessor.extract_decision(replies)
            except Exception as e:
                print(f"    DEBUG: Error in extract_decision: {e}")
                raise

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
            
        except Exception as e:
            print(f"    DEBUG: Error building paper record for submission {getattr(submission, 'id', 'unknown')}")
            print(f"    DEBUG: Error type: {type(e).__name__}")
            print(f"    DEBUG: Error message: {str(e)}")
            raise