content = open('packages/security/enterprise.py').read()

# The authenticate method doesn't check password. Fix it.
old = '''    def authenticate(self, username: str, password: str, ip: str = None) -> bool:
        """Authenticate user."""
        user = self.users.get(username)
        if not user:
            self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", False, "User not found")
            return False
        
        # IP restriction
        if user.allowed_ips and ip and ip not in user.allowed_ips:
            self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", False, f"IP {ip} not allowed")
            return False
        
        # MFA check
        if user.mfa_enabled:
            # In production, verify MFA code here
            self.audit_logger.log_event("AUTH", username, "MFA_REQUIRED", "auth", True)
        
        self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", True)
        return True'''

new = '''    def authenticate(self, username: str, password: str, ip: str = None) -> bool:
        """Authenticate user with password verification."""
        user = self.users.get(username)
        if not user:
            self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", False, "User not found")
            return False
        
        # Password verification (hash-based)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user.api_key_hash:
            self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", False, "Wrong password")
            return False
        
        # IP restriction
        if user.allowed_ips and ip and ip not in user.allowed_ips:
            self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", False, f"IP {ip} not allowed")
            return False
        
        # MFA check
        if user.mfa_enabled:
            # In production, verify MFA code here
            self.audit_logger.log_event("AUTH", username, "MFA_REQUIRED", "auth", True)
        
        self.audit_logger.log_event("AUTH", username, "LOGIN", "auth", True)
        return True'''

content = content.replace(old, new)

# Also fix create_user to store password hash properly
old_create = '''        api_key = secrets.token_urlsafe(32)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()'''

new_create = '''        api_key = secrets.token_urlsafe(32)
        # Store the PASSWORD hash for authentication (not the API key)
        api_key_hash = hashlib.sha256(password.encode()).hexdigest()'''

content = content.replace(old_create, new_create)

open('packages/security/enterprise.py', 'w').write(content)
print('Fixed authentication - now verifies password')
