import { Button, Col, Row, Table } from "antd";
import ButtonGroup from "antd/es/button/button-group";

export interface DataType {
    key: React.Key;
    name: string;
    email: string;
    importanceScore: number;
    repliedFraction: number;
    valueProp: number;
    emailsSent: number;
  }

type AddressTableProps = {
    sender: Map<string, string>;
    addresses: DataType[];
    onSplit: (action: string, sender, address: string) => void;
}

function AddressTable({sender, addresses, onSplit}: AddressTableProps) : React.ReactElement {
   
    const createButton = (action, address, label) => (
        <Button 
            disabled={address['disabled']}
            onClick={() => onSplit(action, sender, address['id'])}>{label}
        </Button>
    )

    const actionColumn = {
        title: 'Action',
        dataIndex: 'id',
        key: 'id',
        render: (status, row) => {
            return <ButtonGroup>
                {createButton('keep', row, 'Keep')}
                {createButton('clean', row, 'Clean')}
                {createButton('split', row, 'Split')}
            </ButtonGroup>
        },
    };

    const columns = [
        actionColumn,
        IMPORTANCE_COLUMN,
        SENDER_COLUMN,
        EMAIL_COUNT_COLUMN,
        READ_PERCENT_COLUMN,
        REPLIED_PERCENT,
        IMPORTANCE_PERCENT_COLUMN
      ]
    return <Table
        columns={columns}
        rowKey="id"
        dataSource={addresses}
        pagination={{ pageSize: 10 }}       
        />
}

export const renderAddresses = (row, onSplit: (action: string, sender, address: string) => void) : React.ReactElement => {
    const addresses = row['addresses'];
 
    

    
    return <AddressTable sender={row} addresses={addresses} onSplit={onSplit} />
}

//     return <>
//         <Row gutter={18}>
//         <Col span={2}></Col>
//         <Col span={4}></Col>
//         <Col span={12}>Address</Col>
//         <Col span={2}>Email Count</Col>
//         </Row>
//         {addresses.map((address, index) => (
//             <Row key={index} gutter={18} className={address['disabled'] ? "disabledAddress" : ""}>
//                 <Col span={2}></Col>
//                 <Col span={4}>
//                     <ButtonGroup>
//                         {createButton('keep', address, 'Keep')}
//                         {createButton('clean', address, 'Clean')}
//                         {createButton('split', address, 'Split')}
//                     </ButtonGroup>
//                 </Col>
//                 <Col span={12}>{`${address["name"]} <`}<a href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent(address["email"])}`} target="_blank" rel="noopener noreferrer">{address["email"]}</a>
//                     {">"} </Col>
//                 <Col span={2}>{address["emailCount"]}</Col>
//             </Row>
//                 ))}
//                 </>
//   };

export const IMPORTANCE_COLUMN = {
    title: 'Importance',
    dataIndex: 'importanceScore',
    key: 'importanceScore',
    render: (importanceScore) => {
        return `${ (importanceScore).toFixed(3)}`
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

export const STATUS_COLUMN = {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    render: (status) => (status === 'none' ? '' : status),
    sorter: (a, b) => a.status - b.status,
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
  dataIndex: 'emailCount',
  key: 'emailCount',
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
