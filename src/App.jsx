import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ackAlert,
  assignAlert,
  reopenAlert,
  changePassword,
  fetchAlertDetail,
  fetchAlerts,
  fetchCurrentUser,
  login,
  logout,
  silenceAlert,
  uploadAvatar,
  updateProfile,
} from './api/auth'
import './App.css'

const rememberKey = 'aiops_remember_username'
const HOME_MENU_KEY = 'home'

const observeRoutes = [
  { key: 'logs', label: '日志中心', path: '/observe/logs' },
  { key: 'alerts', label: '告警中心', path: '/observe/alerts' },
  { key: 'traces', label: '链路追踪', path: '/observe/traces' },
  { key: 'dashboards', label: '监控看板', path: '/observe/dashboards' },
]

const sideMenus = [
  { key: HOME_MENU_KEY, label: '平台首页', icon: 'observe' },
  { key: 'cmdb', label: 'CMDB', icon: 'cmdb' },
  { key: 'hosts', label: '主机中心', icon: 'hosts' },
  { key: 'cloud', label: '多云管理', icon: 'cloud' },
  { key: 'ticket', label: '工单系统', icon: 'ticket' },
  { key: 'container', label: '容器管理', icon: 'container' },
  { key: 'middleware', label: '中间件', icon: 'middleware' },
  {
    key: 'observe',
    label: '可观测性',
    icon: 'observe',
    children: observeRoutes,
  },
]

function MenuIcon({ name }) {
  const common = {
    width: 16,
    height: 16,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  }

  switch (name) {
    case 'cmdb':
      return (
        <svg {...common}>
          <rect x="3" y="4" width="18" height="6" rx="1.5" />
          <rect x="3" y="14" width="18" height="6" rx="1.5" />
        </svg>
      )
    case 'hosts':
      return (
        <svg {...common}>
          <rect x="3" y="5" width="18" height="11" rx="2" />
          <path d="M8 19h8" />
          <path d="M12 16v3" />
        </svg>
      )
    case 'cloud':
      return (
        <svg {...common}>
          <path d="M7.5 18a4 4 0 1 1 .8-7.9A5.5 5.5 0 0 1 19 12a3.5 3.5 0 0 1-1 6H7.5Z" />
        </svg>
      )
    case 'ticket':
      return (
        <svg {...common}>
          <path d="M4 7h16v4a2 2 0 0 0 0 4v4H4v-4a2 2 0 0 0 0-4V7Z" />
          <path d="M12 7v12" />
        </svg>
      )
    case 'container':
      return (
        <svg {...common}>
          <rect x="3" y="7" width="18" height="10" rx="2" />
          <path d="M8 7v10M16 7v10" />
        </svg>
      )
    case 'middleware':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19 12h2M3 12h2M12 3v2M12 19v2M17 7l1.5-1.5M5.5 18.5 7 17M17 17l1.5 1.5M5.5 5.5 7 7" />
        </svg>
      )
    case 'observe':
      return (
        <svg {...common}>
          <path d="M4 19V5" />
          <path d="M9 19v-8" />
          <path d="M14 19v-5" />
          <path d="M19 19V9" />
        </svg>
      )
    default:
      return null
  }
}


function LoginView({ form, onInputChange, onSubmit, onForgotPassword, loading, errorMessage, successMessage, themeClass }) {
  return (
    <main className={`page login-page ${themeClass}`}>
      <section className="login-card" aria-labelledby="login-title">
        <h1 id="login-title">AiOps 登录</h1>
        <p className="subtitle">欢迎回来，请登录你的运维平台账号</p>
        <form className="login-form" onSubmit={onSubmit}>
          <label htmlFor="username">用户名</label>
          <input id="username" name="username" type="text" value={form.username} onChange={onInputChange} placeholder="请输入用户名" autoComplete="username" required />
          <label htmlFor="password">密码</label>
          <input id="password" name="password" type="password" value={form.password} onChange={onInputChange} placeholder="请输入密码" autoComplete="current-password" required />
          <div className="row">
            <label className="remember-me" htmlFor="remember">
              <input id="remember" name="remember" type="checkbox" checked={form.remember} onChange={onInputChange} />记住我
            </label>
            <button type="button" className="link-button" onClick={onForgotPassword}>忘记密码？</button>
          </div>
          {errorMessage ? <p className="message error">{errorMessage}</p> : null}
          {successMessage ? <p className="message success">{successMessage}</p> : null}
          <button type="submit" disabled={loading}>{loading ? '登录中...' : '登录'}</button>
        </form>
      </section>
    </main>
  )
}

function DashboardView({ currentUser, onLogout, onProfileMessage, onUserRefresh, errorMessage, themeClass, themeMode, onThemeModeChange }) {
  const getInitialObservePath = () => {
    const hashPath = window.location.hash?.replace('#', '') || '/observe/alerts'
    return observeRoutes.some((item) => item.path === hashPath) ? hashPath : '/observe/alerts'
  }

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('aiops_sidebar_collapsed') === 'true')
  const [observeExpanded, setObserveExpanded] = useState(() => sessionStorage.getItem('aiops_observe_expanded') === 'true')
  const [activeMenuKey, setActiveMenuKey] = useState(() => {
    const hashPath = window.location.hash?.replace('#', '') || ''
    if (observeRoutes.some((item) => item.path === hashPath)) {
      return 'observe'
    }
    const stored = sessionStorage.getItem('aiops_last_active_menu')
    return sideMenus.some((item) => item.key === stored) ? stored : HOME_MENU_KEY
  })
  const [currentObservePath, setCurrentObservePath] = useState(getInitialObservePath)
  const [menuOpen, setMenuOpen] = useState(false)
  const [noticeOpen, setNoticeOpen] = useState(false)
  const noticeWrapRef = useRef(null)
  const userMenuRef = useRef(null)
  const [avatarModalOpen, setAvatarModalOpen] = useState(false)
  const [passwordModalOpen, setPasswordModalOpen] = useState(false)
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [themeModalOpen, setThemeModalOpen] = useState(false)

  const [avatarFile, setAvatarFile] = useState(null)
  const [avatarPreview, setAvatarPreview] = useState('')
  const [passwordForm, setPasswordForm] = useState({ oldPassword: '', newPassword: '', confirmPassword: '' })
  const [profileForm, setProfileForm] = useState({ email: currentUser.email || '', phone: currentUser.phone || '' })
  const [alertFilters, setAlertFilters] = useState({ level: 'all', status: 'all', service: 'all', q: '', page: 1, page_size: 10 })
  const alertBoardRef = useRef(null)
  const [alerts, setAlerts] = useState([])
  const [noticeAlerts, setNoticeAlerts] = useState([])
  const [alertServices, setAlertServices] = useState([])
  const [alertTotal, setAlertTotal] = useState(0)
  const [alertTotalPages, setAlertTotalPages] = useState(1)
  const [alertLoading, setAlertLoading] = useState(false)
  const [noticeRefreshing, setNoticeRefreshing] = useState(false)
  const [alertsSyncedAt, setAlertsSyncedAt] = useState('')
  const [alertDetailOpen, setAlertDetailOpen] = useState(false)
  const [alertDetailLoading, setAlertDetailLoading] = useState(false)
  const [alertDetail, setAlertDetail] = useState(null)
  const [alertActionFilters, setAlertActionFilters] = useState({ action_operator: '', action_from: '', action_to: '', action_limit: '50' })
  const [alertOperators, setAlertOperators] = useState([])

  useEffect(() => {
    localStorage.setItem('aiops_sidebar_collapsed', String(sidebarCollapsed))
  }, [sidebarCollapsed])

  useEffect(() => {
    sessionStorage.setItem('aiops_observe_expanded', String(observeExpanded))
  }, [observeExpanded])

  useEffect(() => {
    const onDocumentClick = (event) => {
      if (noticeWrapRef.current && !noticeWrapRef.current.contains(event.target)) {
        setNoticeOpen(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', onDocumentClick)
    return () => {
      document.removeEventListener('mousedown', onDocumentClick)
    }
  }, [])

  useEffect(() => {
    const onHashChange = () => {
      const path = window.location.hash?.replace('#', '') || ''
      if (observeRoutes.some((item) => item.path === path)) {
        setCurrentObservePath(path)
        setActiveMenuKey('observe')
      }
    }

    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    sessionStorage.setItem('aiops_last_active_menu', activeMenuKey)
  }, [activeMenuKey])

  useEffect(() => {
    const getPageKey = () => {
      if (activeMenuKey === 'observe') {
        return `observe:${currentObservePath}`
      }
      return activeMenuKey
    }

    const saveScroll = () => {
      sessionStorage.setItem('aiops_last_page_key', getPageKey())
      sessionStorage.setItem('aiops_last_scroll_y', String(window.scrollY))
    }

    const restoreScroll = () => {
      const pageKey = sessionStorage.getItem('aiops_last_page_key')
      const scrollY = Number(sessionStorage.getItem('aiops_last_scroll_y') || '0')
      if (!pageKey || Number.isNaN(scrollY)) return

      const currentKey = getPageKey()
      if (pageKey === currentKey) {
        window.requestAnimationFrame(() => {
          window.scrollTo({ top: scrollY, behavior: 'auto' })
        })
      }
    }

    window.addEventListener('scroll', saveScroll, { passive: true })
    window.addEventListener('beforeunload', saveScroll)
    restoreScroll()

    return () => {
      window.removeEventListener('scroll', saveScroll)
      window.removeEventListener('beforeunload', saveScroll)
    }
  }, [activeMenuKey, currentObservePath])

  const avatarText = useMemo(() => currentUser.username[0]?.toUpperCase() || 'U', [currentUser.username])

  const loadAlerts = async (filters = alertFilters) => {
    setAlertLoading(true)
    try {
      const result = await fetchAlerts(filters)
      setAlerts(result.items || [])
      setAlertServices(result.services || [])
      setAlertTotal(result.total || 0)
      setAlertTotalPages(result.total_pages || 1)
      setAlertsSyncedAt(new Date().toLocaleTimeString())
    } catch (error) {
      const rawMessage = error.message || ''
      const friendly = rawMessage.includes('Not Found') ? '告警服务暂不可用，请刷新页面后重试。' : (rawMessage || '加载告警失败，请稍后重试。')
      onProfileMessage(friendly, true)
    } finally {
      setAlertLoading(false)
    }
  }
  const loadNoticeAlerts = async () => {
    const result = await fetchAlerts({ level: 'all', status: 'all', service: 'all', q: '', page: 1, page_size: 100 })
    setNoticeAlerts(result.items || [])
    setAlertsSyncedAt(new Date().toLocaleTimeString())
  }

  const reminderSections = useMemo(() => {
    const statusLabelMap = {
      open: '未处理',
      acked: '已确认',
      silenced: '已静默',
    }
    const levelTagMap = {
      P1: '严重告警',
      P2: '重要告警',
      P3: '一般告警',
    }
    const levelDotMap = {
      P1: 'red',
      P2: 'yellow',
      P3: 'blue',
    }

    const alertItems = noticeAlerts.map((alert) => ({
      id: alert.id,
      level: levelDotMap[alert.level] || 'blue',
      title: `${alert.title}（${alert.id}）`,
      tag: levelTagMap[alert.level] || '告警',
      desc: `${alert.service} · ${statusLabelMap[alert.status] || alert.status}${alert.assignee ? ` · 责任人：${alert.assignee}` : ''}`,
      time: alert.time,
    }))

    const pendingCount = noticeAlerts.filter((alert) => alert.status === 'open').length

    const pendingItems = alertItems.filter((item) => item.desc.includes('未处理'))

    return [
      {
        title: '待处理告警',
        count: pendingCount,
        items: pendingItems.slice(0, 3),
      },
      {
        title: '全部告警动态',
        count: noticeAlerts.length,
        items: alertItems.slice(0, 3),
      },
    ]
  }, [noticeAlerts])

  const totalReminderCount = useMemo(
    () => noticeAlerts.filter((item) => item.status === 'open').length,
    [noticeAlerts],
  )

  const metrics = useMemo(() => {
    const pendingCount = noticeAlerts.filter((item) => item.status === 'open').length
    const logSourceCount = alertServices.length
    const traceCount = noticeAlerts.filter((item) => item.level === 'P1' || item.level === 'P2').length
    const dashboardCount = new Set(noticeAlerts.map((item) => item.service)).size

    return [
      { label: '日志数据源', value: logSourceCount, type: 'plain' },
      { label: '待处理告警', value: pendingCount, type: 'danger' },
      { label: 'Trace 数', value: traceCount, type: 'warn' },
      { label: '已接入看板', value: dashboardCount, type: 'ok' },
    ]
  }, [noticeAlerts, alertServices])

  const ticketView = useMemo(() => {
    const pendingTickets = noticeAlerts.filter((item) => item.status === 'open')
    const processingTickets = noticeAlerts.filter((item) => item.status === 'acked')
    const completedTickets = noticeAlerts.filter((item) => item.status === 'silenced')

    const recentRows = noticeAlerts.slice(0, 3).map((item, index) => {
      const statusText = item.status === 'open' ? '待处理' : item.status === 'acked' ? '处理中' : '已完成'
      return {
        id: `TK-${3900 + index}`,
        text: `${item.title}（${item.id}）`,
        status: statusText,
      }
    })

    return {
      summary: [
        { value: pendingTickets.length, label: '待处理', type: 'danger' },
        { value: processingTickets.length, label: '处理中', type: 'warn' },
        { value: completedTickets.length, label: '今日已完成', type: 'ok' },
        { value: pendingTickets.length ? '28m' : '0m', label: '平均响应时长', type: 'plain' },
      ],
      recentRows,
    }
  }, [noticeAlerts])

  const onAvatarFileChange = (event) => {
    const file = event.target.files?.[0] || null
    setAvatarFile(file)
    setAvatarPreview('')

    if (!file) {
      return
    }

    if (file.size > 2 * 1024 * 1024) {
      onProfileMessage('头像文件不能超过 2MB。', true)
      setAvatarFile(null)
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = String(reader.result || '')
      const image = new Image()
      image.onload = () => {
        if (image.width < 128 || image.height < 128) {
          onProfileMessage('头像尺寸至少需要 128x128。', true)
          setAvatarFile(null)
          setAvatarPreview('')
          return
        }
        setAvatarPreview(dataUrl)
      }
      image.onerror = () => {
        onProfileMessage('图片读取失败，请更换文件。', true)
        setAvatarFile(null)
      }
      image.src = dataUrl
    }
    reader.readAsDataURL(file)
  }

  const saveAvatar = async () => {
    if (!avatarFile) {
      onProfileMessage('请先选择头像文件。', true)
      return
    }

    try {
      const result = await uploadAvatar(avatarFile)
      setAvatarModalOpen(false)
      setMenuOpen(false)
      setAvatarFile(null)
      setAvatarPreview('')
      onProfileMessage(result.message || '头像已更新。')
      await onUserRefresh()
    } catch (error) {
      onProfileMessage(error.message || '头像修改失败，请稍后再试。', true)
    }
  }

  const onAlertFilterChange = (name, value) => {
    setAlertFilters((prev) => ({ ...prev, [name]: value, page: 1 }))
  }

  const currentObserveRoute = useMemo(
    () => observeRoutes.find((item) => item.path === currentObservePath) || observeRoutes[1],
    [currentObservePath],
  )

  const currentPrimaryMenu = useMemo(
    () => sideMenus.find((item) => item.key === activeMenuKey) || sideMenus.find((item) => item.key === HOME_MENU_KEY) || sideMenus[0],
    [activeMenuKey],
  )

  const navigateObserve = (path) => {
    if (!observeRoutes.some((item) => item.path === path)) return
    setActiveMenuKey('observe')
    setObserveExpanded(true)
    setCurrentObservePath(path)
    window.location.hash = path
  }

  const onPrimaryMenuClick = (menu) => {
    if (menu.key === HOME_MENU_KEY) {
      setActiveMenuKey(HOME_MENU_KEY)
      setObserveExpanded(false)
      return
    }
    if (menu.key === 'observe') {
      setActiveMenuKey('observe')
      setObserveExpanded((prev) => !prev)
      return
    }
    setActiveMenuKey(menu.key)
    setObserveExpanded(false)
  }

  const goHome = () => {
    setActiveMenuKey(HOME_MENU_KEY)
    setObserveExpanded(false)
    window.location.hash = ''
  }

  const scrollToAlertBoard = () => {
    alertBoardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const onNoticeRefresh = async (silent = false) => {
    setNoticeRefreshing(true)
    try {
      await loadNoticeAlerts()
      if (!silent) {
        onProfileMessage('提醒已刷新。')
      }
    } catch (error) {
      if (!silent) {
        onProfileMessage(error.message || '提醒刷新失败，请稍后重试。', true)
      }
    } finally {
      setNoticeRefreshing(false)
    }
  }

  const onNoticeViewMore = async (sectionTitle) => {
    const nextFilters =
      sectionTitle === '待处理告警'
        ? { ...alertFilters, status: 'open', page: 1 }
        : { level: 'all', status: 'all', service: 'all', q: '', page: 1, page_size: 10 }

    setAlertFilters(nextFilters)
    await loadAlerts(nextFilters)
    navigateObserve('/observe/alerts')
    setNoticeOpen(false)
    scrollToAlertBoard()
    onProfileMessage(sectionTitle === '待处理告警' ? '已定位到待处理告警列表。' : '已定位到全部告警列表。')
  }

  const onAlertSearch = async () => {
    await loadAlerts(alertFilters)
  }

  const toIsoWithTimezone = (localValue) => {
    if (!localValue) return ''
    const date = new Date(localValue)
    if (Number.isNaN(date.getTime())) return ''
    return date.toISOString()
  }

  const loadAlertDetail = async (alertId, filters = alertActionFilters) => {
    const payload = {
      action_operator: filters.action_operator || '',
      action_from: toIsoWithTimezone(filters.action_from),
      action_to: toIsoWithTimezone(filters.action_to),
      action_limit: Number(filters.action_limit || 50),
    }
    const result = await fetchAlertDetail(alertId, payload)
    setAlertDetail(result)
    return result
  }

  const openAlertDetail = async (alertId) => {
    setAlertActionFilters({ action_operator: '', action_from: '', action_to: '', action_limit: '50' })
    setAlertDetailOpen(true)
    setAlertDetailLoading(true)
    try {
      const result = await loadAlertDetail(alertId, { action_operator: '', action_from: '', action_to: '', action_limit: '50' })
      const operators = [...new Set((result.actions || []).map((item) => item.operator).filter(Boolean))]
      setAlertOperators(operators)
    } catch (error) {
      onProfileMessage(error.message || '加载告警详情失败', true)
      setAlertDetailOpen(false)
    } finally {
      setAlertDetailLoading(false)
    }
  }

  const onAlertAction = async (action, alertId, currentStatus) => {
    if (action === 'ack' && currentStatus && currentStatus !== 'open') {
      onProfileMessage('仅 open 状态可确认', true)
      return
    }
    if (action === 'silence' && currentStatus && currentStatus === 'silenced') {
      onProfileMessage('该告警已静默', true)
      return
    }
    if (action === 'reopen' && currentStatus && currentStatus !== 'silenced') {
      onProfileMessage('仅已静默告警可重新打开', true)
      return
    }

    try {
      if (action === 'ack') {
        const result = await ackAlert(alertId)
        onProfileMessage(result.message)
      }
      if (action === 'silence') {
        const result = await silenceAlert(alertId)
        onProfileMessage(result.message)
      }
      if (action === 'assign') {
        const assignee = window.prompt('请输入指派人（如：admin / ops）')
        if (!assignee) return
        const result = await assignAlert(alertId, assignee)
        onProfileMessage(result.message)
      }
      if (action === 'reopen') {
        const result = await reopenAlert(alertId)
        onProfileMessage(result.message)
      }
      await loadAlerts(alertFilters)
      await loadNoticeAlerts()
      if (alertDetailOpen && alertDetail?.id === alertId) {
        await loadAlertDetail(alertId)
      }
    } catch (error) {
      onProfileMessage(error.message || '告警操作失败', true)
    }
  }

  const saveProfile = async () => {
    const email = profileForm.email.trim()
    const phone = profileForm.phone.trim()

    if (!email || !phone) {
      onProfileMessage('请完整填写邮箱和手机号。', true)
      return
    }
    if (!email.includes('@')) {
      onProfileMessage('邮箱格式不正确。', true)
      return
    }
    if (!/^1\d{10}$/.test(phone)) {
      onProfileMessage('手机号需为 11 位大陆手机号。', true)
      return
    }

    try {
      const result = await updateProfile({ email, phone })
      await onUserRefresh()
      setProfileModalOpen(false)
      setMenuOpen(false)
      onProfileMessage(result.message || '用户信息已更新。')
    } catch (error) {
      onProfileMessage(error.message || '用户信息更新失败，请稍后再试。', true)
    }
  }

  const savePassword = async () => {
    if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
      onProfileMessage('请完整填写密码信息。', true)
      return
    }
    if (passwordForm.newPassword.length < 6) {
      onProfileMessage('新密码至少 6 位。', true)
      return
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      onProfileMessage('两次输入的新密码不一致。', true)
      return
    }

    try {
      const result = await changePassword({
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      })
      setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' })
      setPasswordModalOpen(false)
      setMenuOpen(false)
      onProfileMessage(result.message || '密码已更新。')
    } catch (error) {
      onProfileMessage(error.message || '密码修改失败，请稍后再试。', true)
    }
  }

  useEffect(() => {
    loadAlerts(alertFilters)
    onNoticeRefresh(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!noticeOpen) return
    onNoticeRefresh(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noticeOpen])

  return (
    <main className={`dashboard-page ${sidebarCollapsed ? 'is-collapsed' : ''} ${themeClass}`}>
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="brand-row">
          <button type="button" className="brand" onClick={goHome} title="返回平台首页">AiOps</button>
          <button type="button" className="collapse-btn" onClick={() => setSidebarCollapsed((prev) => !prev)} title="折叠/展开侧边栏">
            <span className="collapse-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="4" y="5" width="16" height="14" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
                <path d="M10 8.5v7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                <path d={sidebarCollapsed ? 'M14 12h-3' : 'M11.5 12h3'} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                <path d={sidebarCollapsed ? 'M12.8 10.3 14.7 12l-1.9 1.7' : 'M13.2 10.3 11.3 12l1.9 1.7'} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </button>
        </div>

        <nav>
          {sideMenus.map((menu) => {
            const isObserve = menu.key === 'observe'
            const active = menu.key === activeMenuKey
            return (
              <div key={menu.key} className="menu-block">
                <button type="button" className={`menu-item ${active ? 'active' : ''} ${sidebarCollapsed ? 'collapsed' : ''}`} onClick={() => onPrimaryMenuClick(menu)} title={menu.label}>
                  <span className="menu-icon" aria-hidden="true"><MenuIcon name={menu.icon} /></span>
                  {!sidebarCollapsed ? <span className="menu-label">{menu.label}</span> : null}
                  {!sidebarCollapsed && isObserve ? <span className="menu-arrow">{observeExpanded ? '▾' : '▸'}</span> : null}
                </button>
                {!sidebarCollapsed && isObserve && observeExpanded ? (
                  <div className="sub-menu">
                    {menu.children.map((child) => (
                      <button
                        type="button"
                        key={child.path}
                        className={`sub-menu-item ${currentObservePath === child.path ? 'active' : ''}`}
                        onClick={() => navigateObserve(child.path)}
                      >
                        {child.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            )
          })}
        </nav>
      </aside>

      <section className="dashboard-main">
        <header className="topbar">
          <div className="topbar-title">{activeMenuKey === HOME_MENU_KEY ? '平台首页' : activeMenuKey === 'observe' ? `可观测性 / ${currentObserveRoute.label}` : currentPrimaryMenu.label}</div>
          <div className="topbar-actions">
            <div className="notice-wrap" ref={noticeWrapRef}>
              <button
                type="button"
                className="notice-btn"
                onClick={() => setNoticeOpen((prev) => !prev)}
                title="平台提醒"
              >
                <span className="notice-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M12 4a5 5 0 0 0-5 5v2.6c0 .7-.25 1.38-.7 1.92L4.6 15.5c-.5.56-.1 1.45.64 1.45h13.52c.74 0 1.14-.9.64-1.45l-1.7-1.98a2.9 2.9 0 0 1-.7-1.92V9a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                  </svg>
                </span>
                <span className="notice-badge">{totalReminderCount}</span>
              </button>
              {noticeOpen ? (
                <div className="notice-popover">
                  <div className="notice-head">
                    <div>
                      <h3>平台提醒</h3>
                      <p>当前有 {totalReminderCount} 条平台提醒动态{alertsSyncedAt ? ` · 最近刷新 ${alertsSyncedAt}` : ''}</p>
                    </div>
                    <button type="button" className="text-btn" onClick={onNoticeRefresh} disabled={noticeRefreshing}>{noticeRefreshing ? '刷新中...' : '刷新'}</button>
                  </div>

                  <div className="notice-body">
                    {reminderSections.map((section) => (
                      <section key={section.title} className="notice-section">
                        <div className="notice-section-head">
                          <div className="notice-section-title-wrap">
                            <strong>{section.title}</strong>
                            <span>{section.count}</span>
                          </div>
                          <button type="button" className="notice-more" onClick={() => onNoticeViewMore(section.title)}>查看更多</button>
                        </div>
                        {section.items.map((item) => (
                          <article
                            key={`${item.title}-${item.time}-${item.desc}`}
                            className="notice-item"
                            onClick={() => {
                              if (!item.id) return
                              setNoticeOpen(false)
                              openAlertDetail(item.id)
                            }}
                          >
                            <span className={`dot ${item.level}`}></span>
                            <div className="notice-item-main">
                              <div className="notice-item-title-row">
                                <h4>{item.title}</h4>
                                <time>{item.time}</time>
                              </div>
                              <div className="notice-item-meta">
                                <em className={item.level === 'red' ? 'danger' : ''}>{item.tag}</em>
                              </div>
                              <p>{item.desc}</p>
                            </div>
                          </article>
                        ))}
                      </section>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="topbar-user-menu" ref={userMenuRef}>
            <button type="button" className="user-trigger" onClick={() => setMenuOpen((prev) => !prev)}>
              {currentUser.avatar_url ? <img src={currentUser.avatar_url} alt="avatar" className="avatar-img" /> : <span className="avatar">{avatarText}</span>}
              <div>
                <strong>{currentUser.username}</strong>
                <p>{currentUser.role === 'admin' ? '平台管理员' : '运维工程师'}</p>
              </div>
              <span className="caret">▾</span>
            </button>
            {menuOpen ? (
              <div className="user-dropdown">
                <button
                  type="button"
                  onClick={() => {
                    setProfileForm({ email: currentUser.email || '', phone: currentUser.phone || '' })
                    setProfileModalOpen(true)
                  }}
                >用户信息</button>
                <button type="button" onClick={() => setAvatarModalOpen(true)}>修改头像</button>
                <button type="button" onClick={() => setPasswordModalOpen(true)}>修改密码</button>
                <button type="button" onClick={() => setThemeModalOpen(true)}>主题设置</button>
                <button type="button" onClick={onLogout}>退出登录</button>
              </div>
            ) : null}
            </div>
          </div>
        </header>

        <section className="board-card hero"><h1>{activeMenuKey === HOME_MENU_KEY ? 'AiOps 平台首页' : activeMenuKey === 'observe' ? currentObserveRoute.label : currentPrimaryMenu.label}</h1><p>{activeMenuKey === HOME_MENU_KEY ? '统一查看各核心模块状态，点击左侧菜单进入对应功能区。' : '面向持续扩展的模块化页面'}</p></section>
        {errorMessage ? (
          <div className="system-error-toast" role="alert" aria-live="polite">
            <span>{errorMessage}</span>
            <button type="button" onClick={() => onProfileMessage('', false)}>知道了</button>
          </div>
        ) : null}

        {activeMenuKey === 'observe' && currentObservePath === '/observe/alerts' ? (
          <section className="metric-grid">
            {metrics.map((item) => (
              <article className={`metric ${item.type}`} key={item.label}><strong>{item.value}</strong><span>{item.label}</span></article>
            ))}
          </section>
        ) : null}

        <section className="content-grid">
          {activeMenuKey === HOME_MENU_KEY ? (
            <>
              <div className="board-card">
                <h2>平台状态总览</h2>
                <div className="metric-grid">
                  <article className="metric ok"><strong>7</strong><span>核心模块</span></article>
                  <article className="metric plain"><strong>{noticeAlerts.length}</strong><span>平台提醒动态</span></article>
                  <article className="metric warn"><strong>{noticeAlerts.filter((item) => item.status === 'open').length}</strong><span>待处理告警</span></article>
                  <article className="metric danger"><strong>{new Set(noticeAlerts.map((item) => item.service)).size}</strong><span>受影响服务</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>快捷入口</h2>
                <ul className="detail-list">
                  <li><span>可观测性</span><p>查看告警、日志、链路与监控看板</p></li>
                  <li><span>工单系统</span><p>跟踪待处理/处理中/已完成工作项</p></li>
                  <li><span>主机中心</span><p>关注高负载主机与异常节点状态</p></li>
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'observe' && currentObservePath === '/observe/alerts' ? (
            <div className="board-card" ref={alertBoardRef}>
              <h2>告警中心（MVP）</h2>
              <div className="alert-filter-row">
                <select value={alertFilters.level} onChange={(event) => onAlertFilterChange('level', event.target.value)}>
                  <option value="all">全部级别</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
                <select value={alertFilters.status} onChange={(event) => onAlertFilterChange('status', event.target.value)}>
                  <option value="all">全部状态</option>
                  <option value="open">未处理</option>
                  <option value="acked">已确认</option>
                  <option value="silenced">已静默</option>
                </select>
                <select value={alertFilters.service} onChange={(event) => onAlertFilterChange('service', event.target.value)}>
                  <option value="all">全部服务</option>
                  {alertServices.map((service) => (
                    <option key={service} value={service}>{service}</option>
                  ))}
                </select>
                <input value={alertFilters.q} onChange={(event) => onAlertFilterChange('q', event.target.value)} placeholder="搜索标题/服务/ID" />
                <button type="button" className="mini-btn" onClick={onAlertSearch}>查询</button>
              </div>

              <div className="alert-table-wrap">
                <table className="alert-table">
                  <thead>
                    <tr>
                      <th>告警ID</th>
                      <th>级别</th>
                      <th>状态</th>
                      <th>服务</th>
                      <th>标题</th>
                      <th>指派</th>
                      <th>时间</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alertLoading ? (
                      <tr><td colSpan="8">加载中...</td></tr>
                    ) : alerts.length === 0 ? (
                      <tr><td colSpan="8">暂无数据</td></tr>
                    ) : (
                      alerts.map((alert) => (
                        <tr key={alert.id} className="alert-row" onClick={() => openAlertDetail(alert.id)}>
                          <td>{alert.id}</td>
                          <td><span className={`pill ${alert.level.toLowerCase()}`}>{alert.level}</span></td>
                          <td>{alert.status}</td>
                          <td>{alert.service}</td>
                          <td>{alert.title}</td>
                          <td>{alert.assignee || '-'}</td>
                          <td>{alert.time}</td>
                          <td className="ops" onClick={(event) => event.stopPropagation()}>
                            <button
                              type="button"
                              disabled={alert.status !== 'open'}
                              onClick={() => onAlertAction('ack', alert.id, alert.status)}
                            >确认</button>
                            <button
                              type="button"
                              disabled={alert.status === 'silenced'}
                              onClick={() => onAlertAction('silence', alert.id, alert.status)}
                            >静默</button>
                            <button type="button" onClick={() => onAlertAction('assign', alert.id, alert.status)}>指派</button>
                            {alert.status === 'silenced' ? (
                              <button type="button" onClick={() => onAlertAction('reopen', alert.id, alert.status)}>重新打开</button>
                            ) : null}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="alert-pagination">
                <span>第 {alertFilters.page} / {alertTotalPages} 页，共 {alertTotal} 条</span>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={alertFilters.page <= 1 || alertLoading}
                  onClick={async () => {
                    const nextPage = Math.max(1, alertFilters.page - 1)
                    const nextFilters = { ...alertFilters, page: nextPage }
                    setAlertFilters(nextFilters)
                    await loadAlerts(nextFilters)
                  }}
                >上一页</button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={alertFilters.page >= alertTotalPages || alertLoading}
                  onClick={async () => {
                    const nextPage = Math.min(alertTotalPages, alertFilters.page + 1)
                    const nextFilters = { ...alertFilters, page: nextPage }
                    setAlertFilters(nextFilters)
                    await loadAlerts(nextFilters)
                  }}
                >下一页</button>
              </div>
            </div>
          ) : activeMenuKey === 'cmdb' ? (
            <>
              <div className="board-card">
                <h2>CMDB 资源总览</h2>
                <div className="metric-grid">
                  <article className="metric plain"><strong>128</strong><span>配置项总数</span></article>
                  <article className="metric ok"><strong>12</strong><span>业务应用</span></article>
                  <article className="metric warn"><strong>36</strong><span>主机资源</span></article>
                  <article className="metric danger"><strong>4</strong><span>待核对变更</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>最近变更记录</h2>
                <ul className="detail-list">
                  <li><span>03:05</span><p>payment-api 新增依赖 redis-cluster</p></li>
                  <li><span>02:48</span><p>mysql-main 关联业务从 user-center 调整为 order-service</p></li>
                  <li><span>02:12</span><p>k8s-node-03 标签更新：zone=cn-east-1b</p></li>
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'hosts' ? (
            <>
              <div className="board-card">
                <h2>主机健康态势</h2>
                <div className="metric-grid">
                  <article className="metric ok"><strong>28</strong><span>在线主机</span></article>
                  <article className="metric warn"><strong>3</strong><span>高负载主机</span></article>
                  <article className="metric danger"><strong>1</strong><span>待处理异常</span></article>
                  <article className="metric plain"><strong>99.2%</strong><span>整体可用率</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>异常主机清单</h2>
                <div className="alert-table-wrap">
                  <table className="alert-table">
                    <thead>
                      <tr>
                        <th>主机名</th>
                        <th>CPU</th>
                        <th>内存</th>
                        <th>磁盘</th>
                        <th>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr><td>k8s-node-03</td><td>87%</td><td>79%</td><td>88%</td><td>待处理</td></tr>
                      <tr><td>gateway-02</td><td>72%</td><td>68%</td><td>61%</td><td>观察中</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : activeMenuKey === 'cloud' ? (
            <>
              <div className="board-card">
                <h2>多云资源状态</h2>
                <div className="metric-grid">
                  <article className="metric plain"><strong>3</strong><span>云厂商</span></article>
                  <article className="metric ok"><strong>22</strong><span>运行实例</span></article>
                  <article className="metric warn"><strong>2</strong><span>成本预警</span></article>
                  <article className="metric danger"><strong>1</strong><span>网络异常区</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>云资源清单</h2>
                <ul className="detail-list">
                  <li><span>阿里云</span><p>cn-hangzhou：12 台 ECS，网络正常</p></li>
                  <li><span>AWS</span><p>ap-east-1：7 台 EC2，账单接近预算阈值</p></li>
                  <li><span>腾讯云</span><p>ap-guangzhou：3 台 CVM，VPC 路由需复核</p></li>
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'ticket' ? (
            <>
              <div className="board-card">
                <h2>工单处理状态</h2>
                <div className="metric-grid">
                  {ticketView.summary.map((item) => (
                    <article className={`metric ${item.type}`} key={item.label}><strong>{item.value}</strong><span>{item.label}</span></article>
                  ))}
                </div>
              </div>
              <div className="board-card">
                <h2>最近工单</h2>
                <ul className="detail-list">
                  {ticketView.recentRows.map((row) => (
                    <li key={row.id}><span>{row.id}</span><p>{row.text}（{row.status}）</p></li>
                  ))}
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'container' ? (
            <>
              <div className="board-card">
                <h2>容器平台概览</h2>
                <div className="metric-grid">
                  <article className="metric plain"><strong>54</strong><span>运行 Pod</span></article>
                  <article className="metric ok"><strong>12</strong><span>健康 Deployment</span></article>
                  <article className="metric warn"><strong>2</strong><span>重启频繁</span></article>
                  <article className="metric danger"><strong>1</strong><span>CrashLoopBackOff</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>异常工作负载</h2>
                <ul className="detail-list">
                  <li><span>order-worker</span><p>最近 30 分钟重启 6 次</p></li>
                  <li><span>gateway-proxy</span><p>CPU 抖动高于阈值</p></li>
                  <li><span>cmdb-sync</span><p>镜像拉取超时 2 次</p></li>
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'middleware' ? (
            <>
              <div className="board-card">
                <h2>中间件运行态</h2>
                <div className="metric-grid">
                  <article className="metric ok"><strong>5</strong><span>健康组件</span></article>
                  <article className="metric warn"><strong>2</strong><span>性能波动</span></article>
                  <article className="metric danger"><strong>1</strong><span>待处理告警</span></article>
                  <article className="metric plain"><strong>87%</strong><span>平均利用率</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>中间件清单</h2>
                <ul className="detail-list">
                  <li><span>Redis</span><p>命中率 81%，需关注下降趋势</p></li>
                  <li><span>Kafka</span><p>broker-2 lag 偏高（持续 12 分钟）</p></li>
                  <li><span>MySQL</span><p>主从延迟回落到 350ms</p></li>
                </ul>
              </div>
            </>
          ) : activeMenuKey === 'observe' ? (
            <>
              <div className="board-card">
                <h2>{currentObserveRoute.label}</h2>
                <div className="metric-grid">
                  <article className="metric plain"><strong>4</strong><span>模块分区</span></article>
                  <article className="metric ok"><strong>3</strong><span>已接入数据源</span></article>
                  <article className="metric warn"><strong>1</strong><span>优化建议</span></article>
                  <article className="metric danger"><strong>0</strong><span>阻塞问题</span></article>
                </div>
              </div>
              <div className="board-card">
                <h2>模块动态</h2>
                <ul className="detail-list">
                  <li><span>日志中心</span><p>已预留查询入口，待接入日志检索 API</p></li>
                  <li><span>链路追踪</span><p>已建立路由骨架，待补 Trace 查询面板</p></li>
                  <li><span>监控看板</span><p>已建立模块入口，待接入图表组件</p></li>
                </ul>
              </div>
            </>
          ) : (
            <div className="board-card">
              <h2>{currentPrimaryMenu.label}</h2>
              <p>{currentPrimaryMenu.label} 模块已接入导航激活态，可继续按“状态统计 + 列表”模式扩展细节。</p>
            </div>
          )}
        </section>
      </section>

      {alertDetailOpen ? (
        <div className="modal-mask">
          <div className="modal-card alert-detail-modal">
            {alertDetailLoading ? (
              <p>详情加载中...</p>
            ) : alertDetail ? (
              <>
                <h3>{alertDetail.title}</h3>
                <p>{alertDetail.id} · {alertDetail.service} · {alertDetail.level} · {alertDetail.status}</p>

                <div className="detail-block">
                  <strong>影响范围</strong>
                  <p>{alertDetail.impact}</p>
                </div>

                <div className="detail-block">
                  <strong>时间线</strong>
                  <ul className="detail-list">
                    {alertDetail.timeline?.map((item) => (
                      <li key={`${item.time}-${item.event}`}><span>{item.time}</span><p>{item.event}</p></li>
                    ))}
                  </ul>
                </div>

                <div className="detail-block">
                  <strong>处理记录</strong>
                  <div className="alert-action-filter-row">
                    <select
                      value={alertActionFilters.action_operator}
                      onChange={(event) => setAlertActionFilters((prev) => ({ ...prev, action_operator: event.target.value }))}
                    >
                      <option value="">全部操作人</option>
                      {alertOperators.map((operator) => (
                        <option key={operator} value={operator}>{operator}</option>
                      ))}
                    </select>
                    <select
                      value={alertActionFilters.action_limit}
                      onChange={(event) => setAlertActionFilters((prev) => ({ ...prev, action_limit: event.target.value }))}
                    >
                      <option value="20">最近20条</option>
                      <option value="50">最近50条</option>
                      <option value="100">最近100条</option>
                    </select>
                    <button
                      type="button"
                      className="mini-btn"
                      onClick={async () => {
                        if (!alertDetail?.id) return
                        setAlertDetailLoading(true)
                        try {
                          await loadAlertDetail(alertDetail.id)
                        } catch (error) {
                          onProfileMessage(error.message || '筛选处理记录失败', true)
                        } finally {
                          setAlertDetailLoading(false)
                        }
                      }}
                    >筛选</button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={async () => {
                        if (!alertDetail?.id) return
                        const reset = { action_operator: '', action_from: '', action_to: '', action_limit: '50' }
                        setAlertActionFilters(reset)
                        setAlertDetailLoading(true)
                        try {
                          const result = await loadAlertDetail(alertDetail.id, reset)
                          const operators = [...new Set((result.actions || []).map((item) => item.operator).filter(Boolean))]
                          setAlertOperators(operators)
                        } catch (error) {
                          onProfileMessage(error.message || '重置筛选失败', true)
                        } finally {
                          setAlertDetailLoading(false)
                        }
                      }}
                    >重置</button>
                  </div>
                  <ul className="detail-list">
                    {alertDetail.actions?.map((item, idx) => (
                      <li key={`${item.time}-${item.operator}-${idx}`}><span>{item.time}</span><p>{item.operator}：{item.action}</p></li>
                    ))}
                  </ul>
                </div>
              </>
            ) : null}
            <div className="modal-actions">
              {alertDetail ? (
                <>
                  <button
                    type="button"
                    className="mini-btn"
                    disabled={alertDetail.status !== 'open'}
                    onClick={() => onAlertAction('ack', alertDetail.id, alertDetail.status)}
                  >确认</button>
                  <button
                    type="button"
                    className="mini-btn"
                    disabled={alertDetail.status === 'silenced'}
                    onClick={() => onAlertAction('silence', alertDetail.id, alertDetail.status)}
                  >静默</button>
                  <button type="button" className="mini-btn" onClick={() => onAlertAction('assign', alertDetail.id, alertDetail.status)}>指派</button>
                  {alertDetail.status === 'silenced' ? (
                    <button type="button" className="mini-btn" onClick={() => onAlertAction('reopen', alertDetail.id, alertDetail.status)}>重新打开</button>
                  ) : null}
                </>
              ) : null}
              <button type="button" className="secondary-button" onClick={() => setAlertDetailOpen(false)}>关闭</button>
            </div>
          </div>
        </div>
      ) : null}

      {avatarModalOpen ? (
        <div className="modal-mask">
          <div className="modal-card">
            <h3>修改头像</h3>
            <p>请选择本地图片上传（支持 png/jpg/webp，最大 2MB，最小 128x128）</p>
            <input type="file" accept="image/png,image/jpeg,image/jpg,image/webp" onChange={onAvatarFileChange} />
            {avatarPreview ? <img src={avatarPreview} alt="avatar preview" className="avatar-preview" /> : null}
            <div className="modal-actions">
              <button type="button" className="secondary-button" onClick={() => setAvatarModalOpen(false)}>取消</button>
              <button type="button" className="mini-btn" onClick={saveAvatar}>保存</button>
            </div>
          </div>
        </div>
      ) : null}

      {themeModalOpen ? (
        <div className="modal-mask">
          <div className="modal-card">
            <h3>主题设置</h3>
            <p>支持自动按系统时间切换，也可以手动固定主题。</p>

            <div className="theme-preview-grid">
              <button type="button" className={`theme-preview-card ${themeMode === 'auto' ? 'active' : ''}`} onClick={() => onThemeModeChange('auto')}>
                <div className="theme-preview auto">
                  <span className="sun">☀</span>
                  <span className="moon">☾</span>
                </div>
                <div className="theme-preview-text">
                  <strong>自动</strong>
                  <span>07:00-18:59 白天</span>
                </div>
              </button>

              <button type="button" className={`theme-preview-card ${themeMode === 'light' ? 'active' : ''}`} onClick={() => onThemeModeChange('light')}>
                <div className="theme-preview light"></div>
                <div className="theme-preview-text">
                  <strong>白天模式</strong>
                  <span>高亮清晰</span>
                </div>
              </button>

              <button type="button" className={`theme-preview-card ${themeMode === 'dark' ? 'active' : ''}`} onClick={() => onThemeModeChange('dark')}>
                <div className="theme-preview dark"></div>
                <div className="theme-preview-text">
                  <strong>黑夜模式</strong>
                  <span>柔和护眼</span>
                </div>
              </button>
            </div>

            <label className="theme-option"><input type="radio" name="themeMode" checked={themeMode === 'auto'} onChange={() => onThemeModeChange('auto')} /> 自动</label>
            <label className="theme-option"><input type="radio" name="themeMode" checked={themeMode === 'light'} onChange={() => onThemeModeChange('light')} /> 白天模式</label>
            <label className="theme-option"><input type="radio" name="themeMode" checked={themeMode === 'dark'} onChange={() => onThemeModeChange('dark')} /> 黑夜模式</label>
            <div className="modal-actions">
              <button type="button" className="secondary-button" onClick={() => setThemeModalOpen(false)}>关闭</button>
            </div>
          </div>
        </div>
      ) : null}

      {profileModalOpen ? (
        <div className="modal-mask">
          <div className="modal-card">
            <h3>用户信息</h3>
            <p>可编辑邮箱和手机号，保存后将实时更新。</p>
            <p>创建时间：{currentUser.created_at ? new Date(currentUser.created_at).toLocaleString() : '暂无'}</p>
            <p>上次登录：{currentUser.last_login_at ? new Date(currentUser.last_login_at).toLocaleString() : '暂无'}</p>
            <input type="email" placeholder="邮箱" value={profileForm.email} onChange={(event) => setProfileForm((prev) => ({ ...prev, email: event.target.value }))} />
            <input
              type="text"
              inputMode="numeric"
              placeholder="手机号（11位，如 13800138000）"
              value={profileForm.phone}
              onChange={(event) => {
                const digitsOnly = event.target.value.replace(/\D/g, '').slice(0, 11)
                setProfileForm((prev) => ({ ...prev, phone: digitsOnly }))
              }}
            />
            <div className="modal-actions">
              <button type="button" className="secondary-button" onClick={() => setProfileModalOpen(false)}>取消</button>
              <button type="button" className="mini-btn" onClick={saveProfile}>保存信息</button>
            </div>
          </div>
        </div>
      ) : null}

      {passwordModalOpen ? (
        <div className="modal-mask">
          <div className="modal-card">
            <h3>修改密码</h3>
            <p>提交后将调用后端接口实时修改密码。</p>
            <input type="password" placeholder="旧密码" value={passwordForm.oldPassword} onChange={(event) => setPasswordForm((prev) => ({ ...prev, oldPassword: event.target.value }))} />
            <input type="password" placeholder="新密码（至少6位）" value={passwordForm.newPassword} onChange={(event) => setPasswordForm((prev) => ({ ...prev, newPassword: event.target.value }))} />
            <input type="password" placeholder="确认新密码" value={passwordForm.confirmPassword} onChange={(event) => setPasswordForm((prev) => ({ ...prev, confirmPassword: event.target.value }))} />
            <div className="modal-actions">
              <button type="button" className="secondary-button" onClick={() => setPasswordModalOpen(false)}>取消</button>
              <button type="button" className="mini-btn" onClick={savePassword}>更新密码</button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  )
}

function resolveThemeByTime() {
  const hour = new Date().getHours()
  return hour >= 7 && hour < 19 ? 'light' : 'dark'
}

function App() {
  const [form, setForm] = useState({ username: '', password: '', remember: false })
  const [loading, setLoading] = useState(false)
  const [authRestoring, setAuthRestoring] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [currentUser, setCurrentUser] = useState(null)
  const [themeMode, setThemeMode] = useState(() => localStorage.getItem('aiops_theme_mode') || 'auto')
  const [resolvedTheme, setResolvedTheme] = useState(() => {
    const saved = localStorage.getItem('aiops_theme_mode')
    if (saved === 'light' || saved === 'dark') {
      return saved
    }
    return resolveThemeByTime()
  })

  useEffect(() => {
    const rememberedUsername = localStorage.getItem(rememberKey)
    if (rememberedUsername) setForm((prev) => ({ ...prev, username: rememberedUsername, remember: true }))

    const token = localStorage.getItem('aiops_token')
    if (!token) {
      setAuthRestoring(false)
      return
    }

    fetchCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => logout())
      .finally(() => setAuthRestoring(false))
  }, [])

  useEffect(() => {
    localStorage.setItem('aiops_theme_mode', themeMode)

    const applyTheme = () => {
      if (themeMode === 'auto') {
        setResolvedTheme(resolveThemeByTime())
      } else {
        setResolvedTheme(themeMode)
      }
    }

    applyTheme()
    if (themeMode !== 'auto') {
      return
    }

    const timer = window.setInterval(applyTheme, 60 * 1000)
    return () => window.clearInterval(timer)
  }, [themeMode])

  const onInputChange = (event) => {
    const { name, value, type, checked } = event.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const onForgotPassword = () => {
    setErrorMessage('')
    setSuccessMessage('请联系管理员重置密码，或通过企业邮箱找回。')
  }

  const onLogout = () => {
    logout()
    setCurrentUser(null)
    setSuccessMessage('已安全退出登录。')
    setErrorMessage('')
  }

  const onProfileMessage = (message, isError = false) => {
    if (isError) {
      setErrorMessage(message)
      setSuccessMessage('')
      return
    }
    setSuccessMessage(message)
    setErrorMessage('')
  }

  const onSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setErrorMessage('')
    setSuccessMessage('')
    try {
      const result = await login({ username: form.username.trim(), password: form.password })
      if (form.remember) localStorage.setItem(rememberKey, form.username.trim())
      else localStorage.removeItem(rememberKey)
      localStorage.setItem('aiops_token', result.token)
      localStorage.setItem('aiops_refresh_token', result.refresh_token)
      localStorage.setItem('aiops_user', JSON.stringify(result.user))
      setCurrentUser(result.user)
      setSuccessMessage(`登录成功，欢迎你：${result.user?.username ?? form.username}（${result.user?.role ?? 'unknown'}）`)
    } catch (error) {
      setErrorMessage(error.message || '登录失败，请检查后重试')
    } finally {
      setLoading(false)
    }
  }

  const refreshCurrentUser = async () => {
    const latestUser = await fetchCurrentUser()
    localStorage.setItem('aiops_user', JSON.stringify(latestUser))
    setCurrentUser(latestUser)
  }

  const themeClass = resolvedTheme === 'dark' ? 'theme-dark' : 'theme-light'

  if (authRestoring) {
    return (
      <main className={`page login-page ${themeClass}`}>
        <section className="login-card">
          <h1>AiOps</h1>
          <p className="subtitle">正在恢复登录状态...</p>
        </section>
      </main>
    )
  }

  if (currentUser) return <DashboardView currentUser={currentUser} onLogout={onLogout} onProfileMessage={onProfileMessage} onUserRefresh={refreshCurrentUser} errorMessage={errorMessage} themeClass={themeClass} themeMode={themeMode} onThemeModeChange={setThemeMode} />

  return <LoginView form={form} onInputChange={onInputChange} onSubmit={onSubmit} onForgotPassword={onForgotPassword} loading={loading} errorMessage={errorMessage} successMessage={successMessage} themeClass={themeClass} />
}

export default App
