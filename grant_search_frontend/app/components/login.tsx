import { Button, Spin } from 'antd';
import React, { useEffect, useState } from 'react'

export type LoginStatus = {
  loggedIn: boolean;
  userEmail?: string;
}

export default function LoginButton({loginStatus}: {loginStatus: LoginStatus | undefined}) {   
    if (!loginStatus) {
      return <Spin></Spin>
    }
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