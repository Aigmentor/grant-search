
import React from 'react';
import { Table, Button, Row, Col } from 'antd';
import { EMAIL_COUNT_COLUMN, IMPORTANCE_COLUMN, IMPORTANCE_PERCENT_COLUMN, READ_PERCENT_COLUMN, REPLIED_PERCENT, SENDER_COLUMN, STATUS_COLUMN, VALUE_PROP_COLUMN, renderAddresses } from './statsColumns';

  
export const getSenderStats = async () => {
  const response = await fetch('/api/sender_stats');
  const data = await response.json();
  return data;
}
export type Props = {
    stats: any;
    cleanProcess?: boolean;
    onDelete: (ids: string[]) => void;
    onSplit: (action: string, sender, address_id: string) => void;
};

export default function SenderStats({stats, cleanProcess, onDelete, onSplit}: Props) : React.ReactElement {
    const [selectedRowKeys, setSelectedRowKeys] = React.useState([]);
  

  const rowSelection = {
    onChange: (newSelectedRowKeys, selectedRows) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    selectedRowKeys, // This ensures the selected rows are controlled by state
  };

  const callDelete = () => {
    console.log('Delete', selectedRowKeys);
    onDelete(selectedRowKeys);
  }
  const columns = [
    STATUS_COLUMN,
    IMPORTANCE_COLUMN,
    VALUE_PROP_COLUMN,
    SENDER_COLUMN,
    EMAIL_COUNT_COLUMN,
    READ_PERCENT_COLUMN,
    REPLIED_PERCENT,
    IMPORTANCE_PERCENT_COLUMN
  ]

  // Render the Table component with the columns and data defined
  return <div>
    {/* {!isLoading && getThresholds(stats['thresholds'])} */}
    <Button type="primary" onClick={callDelete}>Delete</Button> {/* Step 2: Add Button */}
    <Table
        columns={columns}
        rowKey="id"
        rowSelection={rowSelection}
        dataSource={stats && stats['senders']}
        pagination={{ pageSize: 40 }}
        loading={stats === undefined}
        expandable={{
            expandedRowRender: record => (renderAddresses(record, onSplit)),
            rowExpandable: record => record['addresses'] && record['addresses'].length > 1
          }}
        // rowClassName={(record) => (record.importantSender ? 'important-row' : '')}
        />
    </div>
};

