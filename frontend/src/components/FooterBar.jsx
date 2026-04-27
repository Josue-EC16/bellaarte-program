import { Typography, Space } from 'antd';
import { PhoneOutlined, EnvironmentOutlined, MailOutlined, InstagramOutlined, FacebookOutlined, TikTokOutlined } from '@ant-design/icons';

export function FooterBar() {
  return (
    <footer className="app-footer glass-panel">
      <div className="app-footer-grid">
        <div className="app-footer-section">
          <Typography.Title level={5} style={{ margin: 0 }}>Soporte Técnico</Typography.Title>
          <Space>
            <PhoneOutlined />
            <Typography.Text type="secondary">+591 72053249</Typography.Text>
          </Space>
        </div>

        <div className="app-footer-section">
          <Typography.Title level={5} style={{ margin: 0 }}>Contacto</Typography.Title>
          <Space direction="vertical" size={2}>
            <Space>
              <EnvironmentOutlined />
              <Typography.Text type="secondary"> BELLAARTE BOUTIQUE, LA PAZ</Typography.Text>
            </Space>
            <Space>
              <MailOutlined />
              <Typography.Text type="secondary">bellaarteboutique82@gamil.com</Typography.Text>
            </Space>
          </Space>
        </div>

        <div className="app-footer-section">
          <Typography.Title level={5} style={{ margin: 0 }}>Redes Sociales</Typography.Title>
          <Space size="large" className="app-footer-social">
            <a href="https://www.instagram.com/bellaarte.boutique?igsh=MTc4dTV3cWVoNXcxaw==" target="_blank" rel="noopener noreferrer">
              <InstagramOutlined style={{ fontSize: '24px' }} />
            </a>
            <a href="https://www.facebook.com/share/18gP6cMBSA/" target="_blank" rel="noopener noreferrer">
              <FacebookOutlined style={{ fontSize: '24px' }} />
            </a>
            <a href="https://www.tiktok.com/@bellaarteboutique?is_from_webapp=1&sender_device=pc" target="_blank" rel="noopener noreferrer">
              <TikTokOutlined style={{ fontSize: '24px' }} />
            </a>
          </Space>
        </div>
      </div>
    </footer>
  );
}
