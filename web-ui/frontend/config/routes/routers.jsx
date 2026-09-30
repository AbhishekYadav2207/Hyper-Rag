import NotFoundPage from '@/404'
import App from '@/App'
import ErrorPage from '@/ErrorPage'
import Home from '@/pages/Home'
import Files from '@/pages/Hyper/Files'
import Graph from '@/pages/Hyper/Graph'
import HyperDB from '@/pages/Hyper/DB'
import Setting from '@/pages/Setting'
import APIPage from '@/pages/API'
import { HomeFilled, SmileFilled, FileAddOutlined, QuestionCircleOutlined, DeploymentUnitOutlined, DatabaseOutlined, SettingOutlined, ApiOutlined } from '@ant-design/icons'
import { Navigate } from 'react-router-dom'

export const routers = [
  {
    path: '/',
    element: <Navigate replace to="/Hyper/chat" />
  },
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorPage />,
    icon: <SmileFilled />,
    children: [
      {
        path: '/Hyper/chat',
        name: 'Chat Q&A',
        icon: <QuestionCircleOutlined />,
        // permissionObj: true,
        element: <Home />
      },
      {
        path: '/Hyper/show',
        name: 'HyperGraph',
        icon: <DeploymentUnitOutlined />,
        // permissionObj: true,
        element: <Graph />
      },
      {
        path: '/Hyper/DB',
        name: 'HypergraphDB',
        icon: <DatabaseOutlined />,
        // permissionObj: true,
        element: <HyperDB />
      },
      {
        path: '/Hyper/files',
        name: 'Document Parser',
        icon: <FileAddOutlined />,
        element: <Files />,
      },
      {
        path: '/API',
        name: 'API Docs',
        icon: <ApiOutlined />,
        element: <APIPage />,
      },
      {
        path: '/Setting',
        name: 'Settings',
        icon: <SettingOutlined />,
        // permissionObj: true,
        element: <Setting />
      },
    ]
  },
  { path: '*', element: <NotFoundPage /> }
]
