'use client';

import React, { useEffect, useState } from 'react';
import { Table, Collapse } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import { amountColumn, titleColumn } from '../grants/grantColumns';
import { descriptionColumn } from '../grants/grantColumns';
import { Grant } from '../grants/search';


const UserFavorites: React.FC = () => {
  const [favorites, setFavorites] = useState<Grant[]>([]);
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

  const columns: ColumnsType<Grant> = [
    titleColumn, amountColumn, descriptionColumn
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
