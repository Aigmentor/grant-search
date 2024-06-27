export type Props = {
    onClick: () => void;
    disabled?: boolean;
    children?: React.ReactNode;
};

export default function Button({onClick, disabled, children}: Props) : React.ReactElement {
    return <button
      disabled={disabled}
      onClick={onClick}
      className={`px-4 py-2 text-white font-bold ${disabled ? 'bg-gray-500 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-700'}`}>
        {children}
    </button>
}
