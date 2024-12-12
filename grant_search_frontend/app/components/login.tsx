import { Button } from 'antd';
import React, { useEffect, useState } from 'react'

export default function LoginButton() {
    const [loginStatus, setLoginStatus] = useState<{loggedIn: boolean, userEmail?: string}>({loggedIn: false});
  
    useEffect(() => {
      const checkLoginStatus = async () => {
        try {
          const response = await fetch('/api/user_status');
          const data = await response.json();
          setLoginStatus(data);
        } catch (err) {
          console.error('Error checking login status:', err);
        }
      };
      checkLoginStatus();
    }, []);
  
    return (
      <Button
        onClick={() => {
          window.location.href = loginStatus.loggedIn ? '/auth/logout' : '/auth/login';
        }}
      >
        {loginStatus.loggedIn ? 'Logout' : 'Login'}
      </Button>
    );
  }