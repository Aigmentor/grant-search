'use client';

import React, { useEffect, useState } from 'react';
import { Table, Collapse } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';

interface FavoritedGrant {
  id: string;
  title: string;
  agency: string;
  datasource: string;
  amount: number;
  endDate: string;
  description: string;
  awardUrl: string;
  favorited_at: string;
  comment: string;
}

const UserFavorites: React.FC = () => {
  const [favorites, setFavorites] = useState<FavoritedGrant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFavorites = async () => {
      try {
        const response = await axios.post('/api/favorited_grants');
        setFavorites(response.data.favorited_grants);
      } catch (error) {
        console.error('Error fetching favorites:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchFavorites();
  }, []);

  const columns: ColumnsType<FavoritedGrant> = [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, record: FavoritedGrant) => (
        <span>
          {title}
          <a href={record.awardUrl} target="_blank" rel="noopener noreferrer">
            [link]
          </a>
        </span>
      ),
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `$${amount?.toLocaleString() || 'N/A'}`,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      render: (description: string) => (
        <Collapse ghost>
          <Collapse.Panel
            header={description?.substring(0, 50) + '...'}
            key="1"
          >
            {description}
          </Collapse.Panel>
        </Collapse>
      ),
    },
  ];

  return (
    <div>
      <h2>Afeura Grants</h2>
      <Table
        columns={columns}
        dataSource={favorites}
        loading={loading}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} items`,
        }}
      />
    </div>
  );
};

export default UserFavorites;
