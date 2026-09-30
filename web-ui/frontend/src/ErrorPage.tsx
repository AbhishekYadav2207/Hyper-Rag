import { useRouteError } from 'react-router-dom'

const ErrorPage = () => {
  // Use useRouteError to get route error information
  const error: any = useRouteError()
  console.error(error)

  //  Page refresh
  window.location.reload()

  return <div />
}
export default ErrorPage
