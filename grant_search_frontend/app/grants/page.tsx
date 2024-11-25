'use client';

import React, { useEffect, useState } from "react";
import axios from "axios";
import { Table, Select, Space, Button, Input, Collapse } from "antd";
import type { ColumnsType } from 'antd/es/table';

interface Grant {
  id: string;
  title: string;
  agency: string;
  datasource: string;
  amount: number;
  dueDate: string;
  status: string;
  awardUrl: string;
}

const columns: ColumnsType<Grant> = [
  {
    title: 'Afuera',
    key: 'afuera', 
    render: () => (
      <Button
        type="primary"
        onClick={() => window.open('https://x.com/elonmusk/status/1834104386303520822', '_blank')}
      >
        Afuera
      </Button>
    ),
  },
  {
    title: 'Title',
    dataIndex: 'title',
    key: 'title',
    render: (title: string, record: Grant) => (
      <span> {title}
      <a href={record.awardUrl} target="_blank" rel="noopener noreferrer">
        [link]
      </a>
      </span>
    ),
  },
  {
    title: 'Agency',
    dataIndex: 'agency',
    key: 'agency',
  },
  {
    title: 'Data Source',
    dataIndex: 'datasource',
    key: 'datasource',
  },
  {
    title: 'Amount',
    dataIndex: 'amount',
    key: 'amount',
    render: (amount: number) => `$${amount.toLocaleString()}`,
  },
  {
    title: 'End Date',
    dataIndex: 'endDate',
    key: 'endDate',
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
  {
    title: 'Reason',
    dataIndex: 'reason',
    key: 'reason',
  },
 ];

export default function Grants(): React.ReactElement {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [samplingFraction, setSamplingFraction] = useState(1.0);
  const [agencies, setAgencies] = useState<{id: number, name: string}[]>([]);
  const [queryId, setQueryId] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    agency: '',
    datasource: '',
    text: ''
  });


  useEffect(() => {
    const fetchAgencies = async () => {
      try {
        const response = await axios.get('/api/agencies');
        setAgencies(response.data);
      } catch (error) {
        console.error('Error fetching agencies:', error);
      }
    };

    fetchAgencies();
  }, []);

  const [dataSources, setDataSources] = useState([]);

  useEffect(() => {
    const fetchDataSources = async () => {
      try {
        const response = await axios.get('/api/datasources');
        setDataSources(response.data);
      } catch (error) {
        console.error('Error fetching data sources:', error);
      }
    };

    fetchDataSources();
  }, []);

  useEffect(() => {
    console.log('queryId', queryId);
    if (queryId === undefined) return;

    const pollQueryStatus = async () => {
      try {
        const response = await axios.post('/api/grants_query_status', {
          queryId: queryId
        });

        if (response.data.status === 'success') {
          console.log('grants', response.data.results);
          setGrants(response.data.results);
          console.log('samplingFraction', response.data.sampleFraction);
          setSamplingFraction(response.data.sampleFraction);
          setQueryId(undefined);
          setLoading(false);
        }
      } catch (error) {
        console.error('Error polling query status:', error);
        setLoading(false);
        setQueryId(undefined);
        setSamplingFraction(1.0);
      }
    };

    const intervalId = setInterval(pollQueryStatus, 5000);

    return () => clearInterval(intervalId);
  }, [queryId]);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let progressInterval: NodeJS.Timeout;

    if (loading) {
      setProgress(0);
      progressInterval = setInterval(() => {
        setProgress((prevProgress) => {
          if (prevProgress >= 100) {
            clearInterval(progressInterval);
            return 100;
          }
          return prevProgress + (100/45);
        });
      }, 1000);
    } else {
      setProgress(0);
    }

    return () => {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    };
  }, [loading]);

  const progressBarStyle = {
    height: '4px',
    backgroundColor: '#1890ff',
    width: `${progress}%`,
    transition: 'width 1s linear',
    marginBottom: '20px',
    display: loading ? 'block' : 'none'
  };

  return (
    <div style={{ margin: '40px 20px' }}>
      <h1>Grants</h1>
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
        <Input.TextArea 
          placeholder="Describe the grants you're looking for..." 
          rows={3}
          value={filters.text}
          onChange={(e) => setFilters(prev => ({ ...prev, text: e.target.value }))}
        />
                <Button
          type="primary"
          onClick={() => {
            const fetchGrantsByText = async () => {
              setLoading(true);
              try {
                const response = await axios.post('/api/grants_by_text', { 
                  text: filters.text 
                });
                setQueryId(response.data.queryId);
                setGrants([]);
                setSamplingFraction(1.0);
              } catch (error) {
                console.error('Error fetching grants by text:', error);
                setLoading(false);
              }
            };
            fetchGrantsByText();
          }}
        >
        {loading ? 'Searching...' : 'Search'}
        </Button>
        
        <div style={progressBarStyle}></div>

        <Collapse style={{ marginBottom: 16 }}>
          <Collapse.Panel header="Search Examples" key="1">
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>Find grants about organ donation that end after January 2024</li>
              <li>Show me NIH grants related to cancer research [NIH data not loaded]</li>
              <li>Find grants from the NSF about renewable energy</li>
              <li>Grants featuring womens studies and Physics granted in June 2025</li>
              <li>Find grants awarded to &quot;Mandoye Ndoye&quot; related to DEI</li>
              <li>Show grants focused on DEI initiatives with budgets over $100,000</li>
              <li>Find NSF grants about artificial intelligence from datasource &quot;NSF 2024&quot;</li>
            </ul>
          </Collapse.Panel>
        </Collapse>
      </Space>
{/* 
      <Space style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 200 }}
          placeholder="Filter by Agency"
          allowClear
          onChange={(value) => setFilters(prev => ({ ...prev, agency: value }))}
        >
          {agencies.map(agency => (
            <Select.Option key={agency.id} value={agency.id}>
              {agency.name}
            </Select.Option>
          ))}
        </Select>

        <Select
          style={{ width: 200 }}
          placeholder="Filter by Data Source"
          allowClear
          onChange={(value) => setFilters(prev => ({ ...prev, datasource: value }))}
        >
          {dataSources.map(datasource => (
            <Select.Option key={datasource.id} value={datasource.id}>
              [{datasource.agency_name}] {datasource.name}
            </Select.Option>
          ))}
        </Select>
        <Button 
          type="primary"
          onClick={() => {
            const fetchGrants = async () => {
              setLoading(true);
              try {
                const response = await axios.get('/api/grants', { params: filters });
                setGrants(response.data);
              } catch (error) {
                console.error('Error fetching grants:', error);
              } finally {
                setLoading(false);
              }
            };
            fetchGrants();
          }}
        >
          Search
        </Button> 
      </Space>*/}
        {samplingFraction < 1.0 && <span>Data estimated based on sampling fraction of {Math.round(samplingFraction * 100)}% </span>}
        <br/>
          Totals:<span style={{ marginBottom: 16, fontWeight: 'bold' }}>
          {Math.round(grants.length / samplingFraction)} grants for ${Math.round(grants.reduce((sum, grant) => sum + (grant.amount || 0), 0) / samplingFraction).toLocaleString()}
      </span>

      <Table
        columns={columns}
        dataSource={grants}
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
} 