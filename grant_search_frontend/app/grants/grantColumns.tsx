import { ColumnsType } from "antd/es/table";
import { Grant } from "./search";

export const titleColumn: ColumnsType<Grant>[0] = {
    title: 'Title',
    dataIndex: 'title',
    key: 'title',
    width: 550,
    render: (title: string, record: Grant) => (
      <>
        <span title={title}>{title.length > 100 ? title.substring(0, 100) + '...' : title}</span>
        <a href={record.awardUrl} target="_blank" rel="noopener noreferrer" style={{marginLeft: '0.5em'}}>[link]</a>

      </>
    ),
  };
  
  export const dataSourceColumn: ColumnsType<Grant>[0] = {
    title: 'Data Source',
    dataIndex: 'datasource',
    key: 'datasource',
  };
  
  export const amountColumn: ColumnsType<Grant>[0] = {
    title: 'Amount',
    dataIndex: 'amount',
    key: 'amount',
    defaultSortOrder: 'descend',
    sorter: (a: Grant, b: Grant) => (a.amount || 0) - (b.amount || 0),
    render: (amount: number) => `$${amount?.toLocaleString() || 'N/A'}`,
  };
  
  export const endDateColumn: ColumnsType<Grant>[0] = {
    title: 'End Date',
    dataIndex: 'endDate',
    key: 'endDate',
  };
  
  export const descriptionColumn: ColumnsType<Grant>[0] = {
    title: 'Summary',
    dataIndex: 'summary',
    key: 'summary',
    // render: (description: string) => (
    //   <Collapse ghost>
    //     <Collapse.Panel 
    //       header={description?.substring(0, 50) + '...'} 
    //       key="1"
    //     >
    //       {description}
    //     </Collapse.Panel>
    //   </Collapse>
    // ),
  };
  
  export const reasonColumn: ColumnsType<Grant>[0] = {
    title: 'Reason',
    dataIndex: 'reason',
    key: 'reason',
  };
  