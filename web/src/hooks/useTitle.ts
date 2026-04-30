import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Set document title in the format: `{page} - {appName}`
 * @param page - Current page name
 */
export function useTitle(page: string) {
  const { t } = useTranslation('common')
  const appName = t('appName')

  useEffect(() => {
    document.title = page ? `${page} - ${appName}` : appName
    return () => {
      document.title = appName
    }
  }, [page, appName])
}
