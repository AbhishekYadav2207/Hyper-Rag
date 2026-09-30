import { MenuDataItem } from '@ant-design/pro-components'
import { createBrowserRouter, RouteObject, createHashRouter } from 'react-router-dom'
import { routers } from './routers'

export type RouteType = {
  /** Whether to hide menu layout */
  hideLayout?: boolean
  /** Whether to display in menu bar */
  hideInMenu?: boolean
  /** Permission control: true controls all */
  permissionObj?: {
    /** Page permission control */
    isPagePermission?: boolean
    /** Check if token exists */
    isToken?: boolean
  } & true
  children?: RouteType[]
} & Partial<MenuDataItem> &
  RouteObject

/** Wrap Permission component only on lowest level */
const renderElement = (item: RouteType) => {
  if (item?.element) {
    if (item?.children) {
      return item?.element
    }
    return (
      // <Permission name={item?.name} permissionObj={item?.permissionObj}>
      item?.element
      // </Permission>
    )
  }
  return undefined
}

const reduceRoute: (params: RouteType[]) => RouteType[] = (routesParams: RouteType[]) => {
  return routesParams?.map(item => {
    let curRouter = item
    if (!item?.children) {
      curRouter = {
        ...curRouter,
        element: renderElement(item)
      }
    }
    if (item?.children) {
      curRouter = {
        ...curRouter,
        children: reduceRoute(item?.children) as any
      }
    }
    return curRouter
  })
}

const relRouters = reduceRoute(routers)

export const router = createHashRouter(relRouters)
