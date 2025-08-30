import os
from typing import List, Optional


class NavigationHistory:
    """Handles navigation history for back/forward functionality"""
    
    def __init__(self, max_history: int = 50):
        self.navigation_history: List[str] = []
        self.current_history_index: int = -1
        self.max_history = max_history
    
    def add_to_history(self, path: str) -> None:
        """Add a path to navigation history"""
        if not path or not os.path.exists(path):
            return
            
        # Remove any future history if we're not at the end
        if self.current_history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.current_history_index + 1]
            
        # Add new path to history
        self.navigation_history.append(path)
        self.current_history_index = len(self.navigation_history) - 1
        
        # Limit history size to prevent memory issues
        if len(self.navigation_history) > self.max_history:
            self.navigation_history.pop(0)
            self.current_history_index -= 1
    
    def can_go_back(self) -> bool:
        """Check if we can go back in history"""
        return self.current_history_index > 0
    
    def can_go_forward(self) -> bool:
        """Check if we can go forward in history"""
        return self.current_history_index < len(self.navigation_history) - 1
    
    def go_back(self) -> Optional[str]:
        """Go back to previous directory in history"""
        if self.can_go_back():
            self.current_history_index -= 1
            previous_path = self.navigation_history[self.current_history_index]
            
            if os.path.exists(previous_path):
                return previous_path
            else:
                # If the path no longer exists, try to go back further
                return self.go_back()
        return None
    
    def go_forward(self) -> Optional[str]:
        """Go forward to next directory in history"""
        if self.can_go_forward():
            self.current_history_index += 1
            next_path = self.navigation_history[self.current_history_index]
            
            if os.path.exists(next_path):
                return next_path
            else:
                # If the path no longer exists, try to go forward further
                return self.go_forward()
        return None
    
    def get_current_path(self) -> Optional[str]:
        """Get the current path in history"""
        if 0 <= self.current_history_index < len(self.navigation_history):
            return self.navigation_history[self.current_history_index]
        return None
    
    def clear_history(self) -> None:
        """Clear all navigation history"""
        self.navigation_history.clear()
        self.current_history_index = -1
    
    def get_history_list(self) -> List[str]:
        """Get the full history list"""
        return self.navigation_history.copy()
    
    def get_history_index(self) -> int:
        """Get the current history index"""
        return self.current_history_index
