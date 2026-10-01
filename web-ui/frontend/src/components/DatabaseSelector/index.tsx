import React, { useEffect } from 'react';
import { Select, Typography, Space, Button, message, Spin } from 'antd';
import type { SizeType } from 'antd/es/config-provider/SizeContext';
import { observer } from 'mobx-react';
import { DatabaseOutlined, ReloadOutlined } from '@ant-design/icons';
import { storeGlobalUser } from '../../store/globalUser';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;
const { Option } = Select;

interface DatabaseSelectorProps {
  /** Display mode: selector / button group / compact */
  mode?: 'select' | 'buttons' | 'compact';
  /** Whether to show current database info */
  showCurrent?: boolean;
  /** Whether to show refresh button */
  showRefresh?: boolean;
  /** Selector placeholder text */
  placeholder?: string;
  /** Custom styles */
  style?: React.CSSProperties;
  /** Component size */
  size?: SizeType;
  /** Database change callback */
  onChange?: (value: string) => void;
  /** Whether disabled */
  disabled?: boolean;
}

/**
 * Database selector component
 */
const DatabaseSelector: React.FC<DatabaseSelectorProps> = ({
    mode = 'select',
    showCurrent = true,
    showRefresh = false,
    placeholder,
    style = {},
    size = 'middle',
    onChange,
    disabled = false
}) => {
    const { t } = useTranslation();

    // If placeholder not provided, use default i18n text
    const defaultPlaceholder = placeholder || t('database.select_database_placeholder');

    // Initialize database list
    useEffect(() => {
        if (!storeGlobalUser.selectedDatabase) {
            storeGlobalUser.restoreSelectedDatabase();
        }
        if (storeGlobalUser.availableDatabases.length === 0) {
            storeGlobalUser.loadDatabases();
        }
    }, []);

    // Handle database change
    const handleDatabaseChange = (value) => {
        storeGlobalUser.setSelectedDatabase(value);
        onChange?.(value);
    };

    // Refresh database list
    const handleRefresh = async () => {
        try {
            await storeGlobalUser.loadDatabases();
            message.success(t('database.refresh_success'));
        } catch (error) {
            message.error(t('database.refresh_failed'));
        }
    };

    // Selector mode
    const renderSelectMode = () => (
        <Space size="middle" style={style}>
            <Select
                value={storeGlobalUser.selectedDatabase}
                onChange={handleDatabaseChange}
                style={{ minWidth: 250 }}
                placeholder={placeholder || (storeGlobalUser.availableDatabases.length === 0 ? "No knowledge base yet" : defaultPlaceholder)}
                size={size}
                disabled={disabled}
                loading={storeGlobalUser.databasesLoading}
                dropdownRender={(menu) => (
                    <div>
                        {menu}
                        {showRefresh && (
                            <div style={{ padding: '8px', borderTop: '1px solid #f0f0f0' }}>
                                <Button
                                    type="text"
                                    size="small"
                                    icon={<ReloadOutlined />}
                                    onClick={handleRefresh}
                                    style={{ width: '100%' }}
                                >
                                    Refresh List
                                </Button>
                            </div>
                        )}
                    </div>
                )}
            >
                {storeGlobalUser.availableDatabases.map((db) => (
                    <Option key={db.name} value={db.name}>
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <DatabaseOutlined style={{ marginRight: 6, color: '#1890ff' }} />
                                {db.description}
                            </div>
                        </div>
                    </Option>
                ))}
            </Select>

            {showRefresh && (
                <Button
                    type="text"
                    size={size}
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    disabled={disabled}
                />
            )}
        </Space>
    );

    // Button group mode
    const renderButtonsMode = () => (
        <Space size="small" style={style}>
            {storeGlobalUser.availableDatabases.map((db) => (
                <Button
                    key={db.name}
                    size={size}
                    type={storeGlobalUser.selectedDatabase === db.name ? 'primary' : 'default'}
                    onClick={() => handleDatabaseChange(db.name)}
                    disabled={disabled}
                    icon={<DatabaseOutlined />}
                    title={db.description}
                    style={{
                        borderColor: storeGlobalUser.selectedDatabase === db.name ? '#1890ff' : undefined,
                        borderRadius: '0.5rem'
                    }}
                    className='py-5 px-3'
                >
                    {db.description.replace('Hypergraph', '').replace('Hyper-Graph', '')}
                </Button>
            ))}
            {showRefresh && (
                <Button
                    type="text"
                    size={size}
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    disabled={disabled}
                />
            )}
        </Space>
    );

    // Compact mode
    const renderCompactMode = () => (
        <Space size="small" style={style}>
            <Select
                value={storeGlobalUser.selectedDatabase}
                onChange={handleDatabaseChange}
                style={{ minWidth: 180 }}
                size={size}
                disabled={disabled}
                // bordered={false}
                placeholder={placeholder}
            >
                {storeGlobalUser.availableDatabases.map((db) => (
                    <Option key={db.name} value={db.name} title={db.description}>
                        <DatabaseOutlined style={{ marginRight: 6, color: '#1890ff' }} />
                        {db.description}
                    </Option>
                ))}
            </Select>
        </Space>
    );

    // Loading state
    if (storeGlobalUser.availableDatabases.length === 0) {
        return (
            <Space style={style}>
                <Spin size="small" />
                <Text type="secondary">Loading database list...</Text>
            </Space>
        );
    }

    // Render UI according to mode
    switch (mode) {
        case 'buttons':
            return renderButtonsMode();
        case 'compact':
            return renderCompactMode();
        case 'select':
        default:
            return renderSelectMode();
    }
};

export default observer(DatabaseSelector);