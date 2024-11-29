'use client';

import React, { useEffect, useState } from "react";
import axios from "axios";
import {Button, Form, Input, Select} from "antd";
  
export default function Home() : React.ReactElement {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      await axios.post('/api/upload_datasource', values);
      form.resetFields();
    } catch (error) {
      console.error('Error creating datasource:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto', padding: '0 20px' }}>
      <h1>Create Data Source</h1>
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
      >
        <Form.Item
          label="Name"
          name="name"
          rules={[{ required: true, message: 'Please input the datasource name!' }]}
        >
          <Input placeholder="Enter datasource name" />
        </Form.Item>

        <Form.Item
          label="Agency"
          name="agency"
          rules={[{ required: true, message: 'Please select the datasource type!' }]}
        >
          <Select placeholder="Select datasource type">
            <Select.Option value="NSF" default>NSF</Select.Option>
            <Select.Option value="NIH" default>NIH</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="Source URL" 
          name="sourceUrl"
        >
          <Input.TextArea placeholder="https://www.grants.gov/web/grants/..." />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            Create Data Source
          </Button>
        </Form.Item>
      </Form>
    </div>
  );

   
}