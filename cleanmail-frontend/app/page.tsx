'use client';

import Image from "next/image";
import React, { useEffect, useState } from "react";
import axios from "axios";
import Login from "./components/login";
import {Button} from "antd";
import SenderStats, { getSenderStats } from "./components/senderStats";
  
export default function Home() : React.ReactElement {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(undefined);
  const [status, setStatus] = useState<Map<String, any>>(undefined);
  const [scanDisabled, setScanDisabled] = useState<boolean>(false);
  const [stats, setStats] = React.useState({senders:undefined});

  useEffect(() => {
    axios.get("/api/auth").then((res) => {
      setIsLoggedIn(res.data.isLoggedIn);
      if (!res.data.isLoggedIn) {
        return;
      }
      axios.get("/api/status").then((res) => {
        setStatus(res.data);
      })
      getSenderStats().then((data) => {
        setStats(data);
      });
    });
  }, []);


  if (isLoggedIn === undefined) {
    return <div>Loading...</div>;
  }

  if (!isLoggedIn) {
    return <Login/>
  }
  
  const logout = () => {
    axios.post("/api/logout").then(() => {
      setIsLoggedIn(false);
    });
  }

  const sendScan = () => {
    setScanDisabled(true);
    axios.post("/api/scan_email").then(() => {
    });
  }
  const getStatusBlock = () => {
    const header =  <h1>Welcome to CleanMail {status && `, ${status['email']}`}</h1>
    if (!status) {
      return header;
    }
   
    return <div>
        {header}
        {status['statusData'] &&
          <pre>
          {JSON.stringify(status['statusData'], null, 2)}
          </pre>
        }
        </div>
  };
  
  const refreshStatus = () => {
    axios.get("/api/status").then((res) => {
      setStatus(res.data);
    })
  };

  const onDelete = (ids: string[]) => {
    axios.post("/api/delete_senders", {senders: ids}).then(
      (response) => {
        getSenderStats().then((data) => {
        setStats(data);
        });
      });    
  };

  const onSplit = (address_id: string) => {
    axios.post("/api/split_address", {address: address_id}).then(
      (response) => {
        getSenderStats().then((data) => {
        setStats(data);
        });
      });    
  }

return <div>
    {getStatusBlock()}
    <br/>
    <Button onClick={logout}>Logout</Button> &nbsp;
     <Button onClick={sendScan} disabled={scanDisabled}> Scan Email </Button> &nbsp;
     <Button onClick={refreshStatus}> Refresh Status </Button>
     
    <br/>   
    <br/>
    <SenderStats stats={stats} onDelete={onDelete} onSplit={onSplit}/>
  </div>
}