/* eslint-disable @next/next/no-img-element */
'use client';

import React from "react";
import LoginButton, { useIsLoggedIn } from "../components/login";
import UserSearches from "../components/userSearches";
import UserFavorites from "../components/userFavorites";
import Search from "./search";
import { Tabs } from "antd";


export default function Grants(): React.ReactElement {
  const loginStatus = useIsLoggedIn();

  const items = [
    {
      key: '1',
      label: 'Search',
      children: <Search />,
    },
    {
      key: '2', 
      label: 'Favorited Grants',
      children: <UserFavorites />,
    },
    {
      key: '3',
      label: 'Previous Queries',
      children: <UserSearches />,
    },
  ];
  return (
      <>
    <div style={{ margin: '40px 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>DOGEFuera</h1>
        <LoginButton loginStatus={loginStatus} />
      </div>
      {loginStatus && loginStatus.loggedIn && (        
      <div style={{ marginTop: '20px' }}>
        <Tabs defaultActiveKey="1" items={items}/>
      </div>
      )}
    </div>
        </>
        )
}
