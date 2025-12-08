#!/usr/bin/env python3
"""
Test script for search token functionality

This script tests the search token implementation to ensure:
1. Tokens can be generated
2. Valid tokens allow searches
3. Invalid tokens are rejected
4. Used tokens cannot be reused
5. Expired tokens are rejected
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from app.models import SearchToken
from datetime import datetime, timedelta


def test_token_generation():
    """Test that tokens can be generated"""
    print("Test 1: Token Generation")
    with app.app_context():
        token = SearchToken.generate(ip_address='127.0.0.1')
        assert token is not None, "Token should not be None"
        assert len(token) > 0, "Token should not be empty"
        print(f"  ✓ Generated token: {token[:10]}...")
        return token


def test_token_validation(token):
    """Test that a valid token can be validated"""
    print("\nTest 2: Valid Token Validation")
    with app.app_context():
        result = SearchToken.validate_and_use(token)
        assert result is True, "Valid token should be accepted"
        print("  ✓ Valid token accepted")


def test_token_reuse(token):
    """Test that a used token cannot be reused"""
    print("\nTest 3: Token Reuse Prevention")
    with app.app_context():
        result = SearchToken.validate_and_use(token)
        assert result is False, "Used token should be rejected"
        print("  ✓ Used token rejected")


def test_invalid_token():
    """Test that an invalid token is rejected"""
    print("\nTest 4: Invalid Token Rejection")
    with app.app_context():
        result = SearchToken.validate_and_use("invalid_token_xyz")
        assert result is False, "Invalid token should be rejected"
        print("  ✓ Invalid token rejected")


def test_expired_token():
    """Test that an expired token is rejected"""
    print("\nTest 5: Expired Token Rejection")
    with app.app_context():
        # Create a token
        token = SearchToken.generate(ip_address='127.0.0.1')
        
        # Manually set its created_at to be older than 5 minutes
        search_token = SearchToken.query.filter_by(token=token).first()
        search_token.created_at = datetime.utcnow() - timedelta(minutes=6)
        db.session.commit()
        
        # Try to validate it
        result = SearchToken.validate_and_use(token)
        assert result is False, "Expired token should be rejected"
        print("  ✓ Expired token rejected")


def test_cleanup():
    """Test that old tokens are cleaned up"""
    print("\nTest 6: Token Cleanup")
    with app.app_context():
        # Create some old tokens
        for i in range(3):
            token = SearchToken.generate(ip_address='127.0.0.1')
            search_token = SearchToken.query.filter_by(token=token).first()
            search_token.created_at = datetime.utcnow() - timedelta(hours=2)
            db.session.commit()
        
        # Count tokens before cleanup
        count_before = SearchToken.query.count()
        
        # Run cleanup
        SearchToken.cleanup_old_tokens()
        
        # Count tokens after cleanup
        count_after = SearchToken.query.count()
        
        assert count_after < count_before, "Old tokens should be removed"
        print(f"  ✓ Cleaned up {count_before - count_after} old tokens")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Search Token Implementation Tests")
    print("=" * 60)
    
    try:
        # Test 1: Generate a token
        token = test_token_generation()
        
        # Test 2: Validate the token
        test_token_validation(token)
        
        # Test 3: Try to reuse the token
        test_token_reuse(token)
        
        # Test 4: Try an invalid token
        test_invalid_token()
        
        # Test 5: Test expired token
        test_expired_token()
        
        # Test 6: Test cleanup
        test_cleanup()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

