
import React from 'react';
import { Table } from 'antd';
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
};

export default function SenderStats({stats}: Props) : React.ReactElement {
    const columns: ColumnType<DataType>[] = [
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
      title: 'Sender Name',
      dataIndex: 'name', // Field name in the data object
      key: 'name', // Unique key for each column
    },
    {
      title: 'Email Address',
      dataIndex: 'email',
      key: 'email',
      render: (email) => {
        var emailText = email;
        // Check if the email length is greater than 30 characters
        if (email.length > 30) {
          // If so, truncate to 30 characters and add ellipses
          emailText = `${email.slice(0, 30)}...`;
        }
        return <a href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent(email)}`} target="_blank" rel="noopener noreferrer"> {emailText}</a>
      }
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
 
  // Render the Table component with the columns and data defined
  return <div>
    {/* {!isLoading && getThresholds(stats['thresholds'])} */}
    <Table
        columns={columns}
        dataSource={stats && stats['senders']}
        pagination={{ pageSize: 40 }}
        loading={stats === undefined}
        // rowClassName={(record) => (record.importantSender ? 'important-row' : '')}
        />;
    </div>
};

