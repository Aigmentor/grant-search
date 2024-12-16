import { Collapse, Spin } from "antd";
import { useEffect, useState } from "react";

export default function UserSearches() {
    const [searches, setSearches] = useState<Array<{id: string, query: string, created_at: string}>>([]);
    const [loading, setLoading] = useState(true);
  
    useEffect(() => {
      const fetchSearches = async () => {
        try {
          const response = await fetch('/api/user_searches');
          if (response.ok) {
            const data = await response.json();
            setSearches(data);
          }
        } catch (error) {
          console.error('Error fetching saved searches:', error);
        } finally {
          setLoading(false);
        }
      };
  
      fetchSearches();
    }, []);
  
    if (loading) {
      return <Spin />;
    }
    if (searches.length === 0) {
      return <p>No saved searches found</p>;
    }
    return (
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {searches.map((search) => (
            <li 
              key={search.id}
              style={{
                cursor: 'pointer',
                padding: '8px 0',
                borderBottom: '1px solid #f0f0f0'
              }}
              onClick={() => {
                window.location.href = `/grants?queryId=${search.id}`;
              }}
            >
              <div>{search.query} &nbsp;
              <small style={{ color: '#888' }}>{search.created_at}</small>
              </div>
            </li>
          ))}
        </ul>
    );
  };
  