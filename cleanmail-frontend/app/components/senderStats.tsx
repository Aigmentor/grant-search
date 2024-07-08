
import React from 'react';
import { Table, Button, Row, Col } from 'antd';
import { ColumnType } from 'antd/es/table/interface';

interface DataType {
    key: React.Key;
    name: string;
    email: string;
    importanceScore: number;
    repliedFraction: number;
    valueProp: number;
    emailsSent: number;
  }
  
export const getSenderStats = async () => {
  const response = await fetch('/api/sender_stats');
  const data = await response.json();
  return data;
}
export type Props = {
    stats: any;
    onDelete: (ids: string[]) => void;
    onSplit: (address_id: string) => void;
};

export default function SenderStats({stats, onDelete, onSplit}: Props) : React.ReactElement {
    const [selectedRowKeys, setSelectedRowKeys] = React.useState([]);

    const columns: ColumnType<DataType>[] = [
    {
        title: 'Cleaned',
        dataIndex: 'shouldBeCleaned',
        key: 'shouldBeCleaned',
        render: (shouldBeCleaned) => {
            return (shouldBeCleaned ? 'cleaned' : '');
        },
        filters: [
            { text: 'Active', value: "active" },
            { text: 'Cleaned', value: "cleaned" },
          ],
          onFilter: (value, record) => {
            if (value == "All") {
                return true;
            }
            return record['shouldBeCleaned'] === (value === "cleaned");
        },
    },  
    {
        title: 'Importance',
        dataIndex: 'importanceScore',
        key: 'importanceScore',
        render: (importanceScore) => {
            return `${ (importanceScore * 10000).toFixed(3)}`
        },
        sorter: (a, b) => a.importanceScore - b.importanceScore,
      },
      {
        title: 'Value Prop',
        dataIndex: 'valueProp',
        key: 'valueProp',
        render: (valueProp) => {
            return `${ (valueProp).toFixed(3)}`
        },
        sorter: (a, b) => a.valueProp - b.valueProp,
        defaultSortOrder: 'descend',
      },
    {
      title: 'Sender',
      dataIndex: 'email',
      key: 'email',
      render: (email, row) => {
        const name = row['name'];
        if (name == email) {
            return email;
        }
        const value = `${name} <${email.slice(0, 30)}>`;
        return <a href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent(email)}`} target="_blank" rel="noopener noreferrer"> {value}</a>
      },
      sorter: (a, b) => a.email.localeCompare(b.email),
      filters: [
        { text: 'Show Personal Domains', value: false},
        { text: 'Hide Personal Domains', value: true},
      ],
      defaultFilteredValue: [true],
      onFilter: (value, record) => {
        return !value || !record['personalDomain']
    },
    },
    {
      title: 'Email Count',
      dataIndex: 'emailsSent',
      key: 'emailsSent',
      sorter: (a, b) => a.emailsSent - b.emailsSent,

    },
    {
        title: 'Read %',
        dataIndex: 'readFraction',
        key: 'readFraction',
        render: (readFraction) => {
            return `${ (readFraction * 100).toFixed(2)}%`;
        }
    },
    {
        title: 'Replied %',
        dataIndex: 'repliedFraction',
        key: 'repliedFraction',
        render: (repliedFraction) => {
            return `${ (repliedFraction * 100).toFixed(2)}%`;
        },
        sorter: (a, b) => a.repliedFraction - b.repliedFraction,
    },
    {
        title: 'Important %',
        dataIndex: 'importantFraction',
        key: 'importantFraction',
        render: (importantFraction) => {
            return `${ (importantFraction * 100).toFixed(2)}%`;
        }
    },

    {
        title: 'Email Percentage',
        dataIndex: 'percentOfEmails',
        key: 'percentOfEmails',
        render: (percentOfEmails) => {
            return `${percentOfEmails.toFixed(2)}%`;
        }
    }
  ];
 

  const rowSelection = {
    onChange: (newSelectedRowKeys, selectedRows) => {
      console.log('Selected row keys: ', newSelectedRowKeys);
      console.log('Selected rows: ', selectedRows);
      setSelectedRowKeys(newSelectedRowKeys);
    },
    selectedRowKeys, // This ensures the selected rows are controlled by state
  };

  const callDelete = () => {
    console.log('Delete', selectedRowKeys);
    onDelete(selectedRowKeys);
  }
  const renderAddresses = (row) : React.ReactElement => {
    const addresses = row['addresses'];
    return <>
        <Row gutter={10}>
        <Col span={2}></Col>
        <Col span={8}>Address</Col>
        <Col span={2}>Email Count</Col>
        </Row>
        {addresses.map((address, index) => (
            <Row key={index} gutter={10}>
                <Col span={2}>
                    <Button onClick={() => onSplit(address['id'])}>Split</Button>
                </Col>
                <Col span={8}>{`${address["name"]} <`}
                     <a href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent(address["email"])}`} target="_blank" rel="noopener noreferrer"> {address["email"]}</a>
                    {">"} </Col>
                <Col span={2}>{address["emailCount"]}</Col>
            </Row>
                ))}
                </>
  }
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
            expandedRowRender: record => (renderAddresses(record)),
            rowExpandable: record => record['addresses'] && record['addresses'].length > 1
          }}
        // rowClassName={(record) => (record.importantSender ? 'important-row' : '')}
        />
    </div>
};

