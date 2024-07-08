import { Button, Col, Row } from "antd";

export interface DataType {
    key: React.Key;
    name: string;
    email: string;
    importanceScore: number;
    repliedFraction: number;
    valueProp: number;
    emailsSent: number;
  }


export const renderAddresses = (row, onSplit) : React.ReactElement => {
    const addresses = row['addresses'];
    return <>
        <Row gutter={18}>
        <Col span={4}></Col>
        <Col span={2}></Col>
        <Col span={12}>Address</Col>
        <Col span={2}>Email Count</Col>
        </Row>
        {addresses.map((address, index) => (
            <Row key={index} gutter={18}>
                <Col span={4}></Col>
                <Col span={2}>
                    <Button onClick={() => onSplit(address['id'])}>Split</Button>
                </Col>
                <Col span={12}>{`${address["name"]} <`}<a href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent(address["email"])}`} target="_blank" rel="noopener noreferrer">{address["email"]}</a>
                    {">"} </Col>
                <Col span={2}>{address["emailCount"]}</Col>
            </Row>
                ))}
                </>
  };

export const IMPORTANCE_COLUMN = {
    title: 'Importance',
    dataIndex: 'importanceScore',
    key: 'importanceScore',
    render: (importanceScore) => {
        return `${ (importanceScore * 10000).toFixed(3)}`
    },
    sorter: (a, b) => a.importanceScore - b.importanceScore,
  };

export const VALUE_PROP_COLUMN = {
    title: 'Value Prop',
    dataIndex: 'valueProp',
    key: 'valueProp',
    render: (valueProp) => {
        return `${ (valueProp).toFixed(3)}`
    },
    sorter: (a, b) => a.valueProp - b.valueProp,
    defaultSortOrder: 'descend',
};

export const SENDER_COLUMN =  {
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
  }
};

export const EMAIL_COUNT_COLUMN = {
  title: 'Email Count',
  dataIndex: 'emailsSent',
  key: 'emailsSent',
  sorter: (a, b) => a.emailsSent - b.emailsSent,

};

export const READ_PERCENT_COLUMN = {
    title: 'Read %',
    dataIndex: 'readFraction',
    key: 'readFraction',
    render: (readFraction) => {
        return `${ (readFraction * 100).toFixed(2)}%`;
    }
};

export const REPLIED_PERCENT = {
    title: 'Replied %',
    dataIndex: 'repliedFraction',
    key: 'repliedFraction',
    render: (repliedFraction) => {
        return `${ (repliedFraction * 100).toFixed(2)}%`;
    },
    sorter: (a, b) => a.repliedFraction - b.repliedFraction,
};

export const IMPORTANCE_PERCENT_COLUMN = {
    title: 'Important %',
    dataIndex: 'importantFraction',
    key: 'importantFraction',
    render: (importantFraction) => {
        return `${ (importantFraction * 100).toFixed(2)}%`;
    }
};

export const EMAIL_PERCENT_COLUMN = {
    title: 'Email Percentage',
    dataIndex: 'percentOfEmails',
    key: 'percentOfEmails',
    render: (percentOfEmails) => {
        return `${percentOfEmails.toFixed(2)}%`;
    }
}
