import { Button, Spin } from 'antd';
import React, { useEffect, useState } from 'react'

export type LoginStatus = {
  loggedIn: boolean;
  userEmail?: string;
}


export const useIsLoggedIn = (): LoginStatus | undefined => {
  const [isLoggedIn, setIsLoggedIn] = useState<LoginStatus |undefined>();

  useEffect(() => {
    const checkLoginStatus = async () => {
        try {
          const response = await fetch('/api/user_status');
          const data = await response.json();
          return data;
        } catch (err) {
          console.error('Error checking login status:', err);
          return false;
        }
      };
  
    const checkAuth = async () => {
      try {
        const status = await checkLoginStatus();
        setIsLoggedIn(status);
      } catch (error) {
        setIsLoggedIn({loggedIn: false});
        localStorage.removeItem('authToken'); // Clear invalid token
      }
    };

    checkAuth();
  }, []);

  return isLoggedIn;
};

export default function LoginButton({loginStatus}: {loginStatus: LoginStatus | undefined}) {   
    if (!loginStatus) {
      return <Spin></Spin>
    }
    return (
      <Button
        type={loginStatus.loggedIn ? undefined : 'primary'}
        onClick={() => {
          window.location.href = loginStatus.loggedIn ? '/auth/logout' : '/auth/login';
        }}
      >
        {loginStatus.loggedIn ? 'Logout' : 'Login'}
      </Button>
    );
  }