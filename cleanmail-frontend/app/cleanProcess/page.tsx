'use client';

import React from "react";
import { DataType, EMAIL_COUNT_COLUMN, IMPORTANCE_COLUMN, IMPORTANCE_PERCENT_COLUMN, renderAddresses, REPLIED_PERCENT, SENDER_COLUMN, VALUE_PROP_COLUMN } from "../components/statsColumns";
import { Button, Progress, Table } from "antd";
import axios from "axios";

interface userStatus {
    emailCount: number;
    deletedEmails: number;
    toBeDeletedEmails: number;
    percentToBeDeleted: number;
}

const getNextSenderBatch = async () => {
    const response = await fetch('/api/sender_batch');
    const data = await response.json();
    return data;
  }
export default function Home() : React.ReactElement {
    const [stats, setStats] = React.useState({senders:undefined});
    const [processing, setProcessing] = React.useState(false);
    const [status, setStatus] = React.useState<userStatus>(undefined);
    
    const header = <h1>Welcome to CleanMail</h1>
    const emailStats = status && <div>
        <Progress percent={Number(status['percentToBeDeleted'].toFixed(1))} />

    </div>

    const updateStats = React.useCallback(() => { 
        getNextSenderBatch().then((data) => {
            setStats(data);
            setProcessing(false);
            axios.get("/api/status").then(({data}) => {
                const {
                    emailCount,
                    deletedEmails,
                    toBeDeletedEmails,            
                } = data;
                const percentToBeDeleted = ((toBeDeletedEmails + deletedEmails) * 100.0/ emailCount);
                console.log('Percent to be deleted', percentToBeDeleted, emailCount, deletedEmails, toBeDeletedEmails)
                setStatus({
                    emailCount,
                    deletedEmails,
                    toBeDeletedEmails,
                    percentToBeDeleted
                });
            });    
          });
    }, []);

    React.useEffect(() => {
        updateStats()
    }, [updateStats]);

    const onSplit = async (action: string, sender, address_id: string) => {
        sender['addresses'].forEach((address) => {
            if (address['id'] === address_id) {
                address['disabled'] = true;
            }
        })
        // Force an update when the address is split
        setStats({...stats});
        await axios.post("/api/split_address", {address_id, action});
    };       
    
    const onAction = React.useCallback(async (action: string, id: string) => {
        setProcessing(true)
        await axios.post("/api/update_senders", {senders: [id], action});
        setStats({senders: stats['senders'].filter((sender) => sender['id'] !== id)});
        setProcessing(false)
        }, [stats])

    const processBatch = React.useCallback((action: string) => {
        console.log('Process', action);
        setProcessing(true);
        const ids = stats['senders'].map((sender) => sender['id']);
        axios.post("/api/update_senders", {senders: ids, action}).then(updateStats);
    }, [updateStats, stats])

    return <div>
        {header}
        {emailStats}
        <SenderTable senders={stats['senders']} processing={processing} onSplit={onSplit} onAction={onAction}/>
        <Button.Group>
            <Button disabled={processing} type="primary" onClick={() => processBatch('clean')}>Clean</Button>
            <div style={{ width: '10px' }} />
            <Button disabled={processing} onClick={() => processBatch('clean')}>Keep</Button>
            <div style={{ width: '10px' }} />
            <Button disabled={processing} onClick={() => processBatch('clean')}>Leave</Button>
        </Button.Group>
    </div>
}

const SenderTable = ({senders, onSplit, onAction, processing}) : React.ReactElement => {
    const columns = [
        {
           title: 'Action',
           dataIndex: 'id',
           key: 'id',
           render: (id) => {
                return <>
                    <Button disabled={processing} onClick={() => onAction("keep", id)}>Keep</Button>
                    &nbsp; <Button disabled={processing} onClick={() => onAction("later", id)}>Later</Button>
                    &nbsp; <Button disabled={processing} onClick={() => onAction("clean", id)}>Clean</Button>
                    </>
              }
        },
        IMPORTANCE_COLUMN,
        VALUE_PROP_COLUMN,
        SENDER_COLUMN,
        EMAIL_COUNT_COLUMN,
        REPLIED_PERCENT,
        IMPORTANCE_PERCENT_COLUMN
      ]
    
    return <Table
        columns={columns}
        rowKey="id"
        dataSource={senders}
        pagination={{ pageSize: 40 }}
        loading={senders === undefined}
        expandable={{
            expandedRowRender: record => (renderAddresses(record, onSplit)),
            rowExpandable: record => record['addresses'] && record['addresses'].length > 1
        }}
    />
}