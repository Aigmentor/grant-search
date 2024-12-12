'use client';

import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Table, Select, Space, Button, Input, Collapse, Alert } from "antd";
import type { ColumnsType } from 'antd/es/table';
import LoginButton from "../components/login";

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

let downloadedGrants: Grant[] = [];
const afueraColumn: ColumnsType<Grant>[0] = {
  title: 'Afuera',
  key: 'afuera', 
  render: () => (
    <Button
      type="primary"
      onClick={() => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.8);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        `;
        const image = Math.random() < 0.5 ? "/static/javier-chainsaw.gif" : "/static/javier-milei-afuera.gif"

        overlay.innerHTML = `
          <div style="display:flex; flex-direction:column; align-items:center; gap:20px; padding:20px; background: white; border-radius: 8px;">
            <img 
              width="500" 
              src="${image}"
              alt="Javier Milei gif"
            />
            <div style="display: flex; gap: 10px;">
              <button 
                style="padding: 10px 20px; font-size: 16px; cursor: pointer;"
                onclick="window.open('https://x.com/elonmusk/status/1834104386303520822', '_blank')"
              >
                DOGE
              </button>
              <button
                style="padding: 10px 20px; font-size: 16px; cursor: pointer;"
                onclick="this.closest('.overlay').remove()"
              >
                Sorry, I like waste
              </button>
            </div>
          </div>
        `;

        document.body.appendChild(overlay);
        overlay.className = 'overlay';
        
        overlay.addEventListener('click', (e) => {
          if (e.target === overlay) {
            overlay.remove();
          }
        });
      }}
    >
      Afuera
    </Button>
  ),
};

const titleColumn: ColumnsType<Grant>[0] = {
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
};

const agencyColumn: ColumnsType<Grant>[0] = {
  title: 'Agency',
  dataIndex: 'agency',
  key: 'agency',
};

const dataSourceColumn: ColumnsType<Grant>[0] = {
  title: 'Data Source',
  dataIndex: 'datasource',
  key: 'datasource',
};

const amountColumn: ColumnsType<Grant>[0] = {
  title: 'Amount',
  dataIndex: 'amount',
  key: 'amount',
  defaultSortOrder: 'descend',
  sorter: (a: Grant, b: Grant) => (a.amount || 0) - (b.amount || 0),
  render: (amount: number) => `$${amount?.toLocaleString() || 'N/A'}`,
};

const endDateColumn: ColumnsType<Grant>[0] = {
  title: 'End Date',
  dataIndex: 'endDate',
  key: 'endDate',
};

const descriptionColumn: ColumnsType<Grant>[0] = {
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
};

const reasonColumn: ColumnsType<Grant>[0] = {
  title: 'Reason',
  dataIndex: 'reason',
  key: 'reason',
};

const columns: ColumnsType<Grant> = [
  afueraColumn,
  titleColumn,
  dataSourceColumn,
  amountColumn,
  endDateColumn,
  descriptionColumn,
  reasonColumn
];

const isMobile = () => {
  if (typeof window !== 'undefined') {
    return window.innerWidth <= 768;
  }
  return false;
};

export default function Grants(): React.ReactElement {
  const [queryStatus, setQueryStatus] = useState(undefined);
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
  const [activeColumns, setActiveColumns] = useState<ColumnsType<Grant>>(columns);
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (queryStatus === 'timed_out') {
      setTimedOut(true);
      setLoading(false);
    } else {
      setTimedOut(false);
    }
  }, [queryStatus]);


  useEffect(() => {
    const handleResize = () => {
      if (isMobile()) {
        setActiveColumns([
          titleColumn,
          amountColumn, 
          descriptionColumn,
          afueraColumn,
        ]);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const submitSearch = async (queryText: string, queryId?: number) => {
    try {
      setQueryStatus("Queuing");
      setLoading(true);
      if (queryId === undefined) {
        const response = await axios.post('/api/grants_by_text', { 
          text: queryText 
        });
        queryId = response.data.queryId;
      }
      setQueryId(queryId);
      const newUrl = `${window.location.pathname}?queryId=${queryId}`;
      window.history.pushState({}, '', newUrl);
      setGrants([]);
      setSamplingFraction(1.0);
    } catch (error) {
      console.error('Error fetching grants by text:', error);
      setLoading(false);
    }
  };

  useEffect( () => {
    const params = new URLSearchParams(window.location.search);
    const urlQueryId = params.get('queryId');
    console.log(`URL queryId: ${urlQueryId}`)
    if (urlQueryId) {
      submitSearch('',parseInt(urlQueryId));
    }
  }, [])
  

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
    if (queryId === undefined) return;

    const pollQueryStatus = async () => {
      try {
        const response = await axios.post('/api/grants_query_status', {
          queryId: queryId,
          startIndex: downloadedGrants.length
        });
        const queryText = response.data.queryText;
        if (queryText && filters.text !== queryText) {
          setFilters(prev => ({ ...prev, text: queryText }));
        }
        const status = response.data.status;
        if (status == 'in_progress') {
          setQueryStatus('streaming results...');
        } else {
          setQueryStatus(status);
        }
        const success = status === 'success';
        const timedOut = status === 'timed_out';
        const inProgress = !success && response.data.results;
        if (success || inProgress) {
          // console.log('grants', response.data.results);
          downloadedGrants.push(...response.data.results);
          if (downloadedGrants.length === 0) {
            setGrants(undefined)
          } else {
           setGrants(downloadedGrants.slice(0));
          }
          setSamplingFraction(response.data.sampleFraction);
          console.log(`Status: ${response.data.status} ${success}`)
          if (success || timedOut) {
            downloadedGrants = [];
            setLoading(false);
            setQueryId(undefined);
          }
        }
      } catch (error) {
        console.error('Error polling query status:', error);
        setLoading(false);
        setQueryId(undefined);
        setSamplingFraction(1.0);
      }
    };

    const intervalId = setInterval(pollQueryStatus, 3000);

    return () => clearInterval(intervalId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
          return prevProgress + (100/80);
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

  const afueraImage = <img 
      src="/static/javier_afuera.png" 
      alt="Afuera Lines"
      style={{
        width: '100%',
        height: 'auto'
      }}
    />

    return (
      <>
      <LoginButton />
    <div style={{ margin: '40px 20px' }}>
      <h1>DOGEFuera</h1>
      Find wasteful grants make them go...
      <div className="mobile-only">
        {afueraImage}
      </div>
      <div style={{ display: 'flex', gap: '20px' }}>
        <Space direction="vertical" className="grant-spacing">
          <Input.TextArea 
            placeholder="Describe the grants you're looking for..." 
            rows={3}
            value={filters.text}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitSearch(filters.text);
              }
            }}
            onChange={(e) => setFilters(prev => ({ ...prev, text: e.target.value }))}
          />
          <Button
            type="primary"
            onClick={() => submitSearch(filters.text)}
          >
          {loading ? 'Searching...' : 'Search'}
          </Button>
          
          <div style={{ position: 'relative', marginBottom: '20px' }}>
            {loading && (
              <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', top: '-20px', fontSize: '12px', color: '#666' }}>
                {queryStatus.toUpperCase().replace('_', ' ')}
              </div>
            )}
            <div style={progressBarStyle}></div>
          </div>
    {timedOut &&
      <div style={{ margin: '40px 20px' }}>
        <Alert
          message="Error"
          description="The query timed out.This can happen due to load or if the AI backends are busy.
          Queries can be sped up by limiting the search domain (such as including funding minimums or maximums or restricting to specific months."
          type="error"
          showIcon
          closable={true}
        />
      </div>
    }

          <Collapse style={{ marginBottom: 16 }}>
            <Collapse.Panel header="Search Examples" key="1">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {[
                  "Find NSF grants about BiPOCS and renewable energy",
                  "Show me NIH grants >$500Krelated to cancer research", 
                  "Find grants from the NSF about Global Warming and women's rights",
                  "Grants featuring womens studies and Physics granted in June 2025",
                  "Find grants awarded to \"Evan Flach\" related to DEI",
                  "Show grants focused on DEI initiatives with budgets over $100,000",
                  "Find NSF grants about artificial intelligence from datasource \"NSF 2024\""
                ].map((example, i) => (
                  <li 
                    key={i}
                    onClick={() => {
                      setFilters(prev => ({...prev, text: example}));
                      submitSearch(example);
                    }}
                    style={{cursor: 'pointer'}}
                  >
                    {example}
                  </li>
                ))}
              </ul>
            </Collapse.Panel>
          </Collapse>
        </Space>

        <div className="desktop-only" style={{ 
            width: '40%',
            // display: 'flex',
            justifyContent: 'right', 
            alignItems: 'right',
            // margin: '0 auto',
            // order: 2          
        }}> {afueraImage}
        </div>
      </div>
        {samplingFraction < 1.0 && <span>Data estimated based on sampling fraction of {Math.round(samplingFraction * 100)}% </span>}
        <br/>
          {grants && grants.length > 0 && <span>
              Totals:<span style={{ marginBottom: 16, fontWeight: 'bold' }}>
              {Math.round(grants.length / samplingFraction)} grants for ${Math.round(grants.reduce((sum, grant) => sum + (grant.amount || 0), 0) / samplingFraction).toLocaleString()}
            </span>
        </span>}

      <Table
        columns={activeColumns}
        dataSource={grants}
        loading={loading && (grants && grants.length === 0)}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} items`,
        }}
      />
    </div>
    </>
  );
}