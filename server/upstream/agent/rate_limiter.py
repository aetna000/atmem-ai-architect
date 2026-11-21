import time
import logging
from collections import deque
from threading import Lock

# Setup logger for rate limiter
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter for LLM API calls to prevent exceeding service limits
    
    Implements sliding window rate limiting to ensure no more than 
    max_requests are made within any time_window period.
    """
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed (default: 5)
            time_window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()  # Track request timestamps
        self.lock = Lock()  # Thread safety
    
    def wait_if_needed(self):
        """
        Block execution if making a request would exceed rate limit
        
        Uses sliding window algorithm:
        1. Remove expired requests from tracking
        2. If at limit, sleep until oldest request expires
        3. Record current request timestamp
        """
        with self.lock:
            now = time.time()
            
            # Remove requests outside current time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Check current request count
            current_count = len(self.requests)
            logger.info(f"Rate limiter: {current_count}/{self.max_requests} requests in current window")
            
            # If at rate limit, wait for oldest request to expire
            if current_count >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached! Waiting {sleep_time:.1f}s before next request")
                    time.sleep(sleep_time)
                    # Clean up expired requests after sleep
                    while self.requests and self.requests[0] <= time.time() - self.time_window:
                        self.requests.popleft()
            
            # Record this request
            self.requests.append(time.time())
            logger.info(f"Rate limiter: Request approved, now {len(self.requests)}/{self.max_requests} in window")
