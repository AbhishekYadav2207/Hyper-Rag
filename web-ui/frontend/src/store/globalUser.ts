import { makeAutoObservable } from 'mobx'
import { SERVER_URL } from '../utils'

class GlobalUser {
  userInfo: Partial<User.UserEntity> = {}
  selectedDatabase: string = ''
  availableDatabases: Array<{ name: string; description: string }> = []
  databasesLoading: boolean = false

  constructor() {
    makeAutoObservable(this)
  }

  async getUserDetail() {
    this.userInfo = {
      roles: [
        {
          id: 5,
          name: 'Super Admin',
          description: 'Has full view and operation permissions',
          adminCount: 0,
          status: 1,
          sort: 5
        }
      ],
      icon: '/logo.png',
      username: 'admin'
    }
  }

  setUserInfo(user: Partial<User.UserEntity>) {
    this.userInfo = user
  }

  // Set current selected database
  setSelectedDatabase(database: string) {
    this.selectedDatabase = database
    // Save to localStorage
    localStorage.setItem('selectedDatabase', database)
  }

  // Set available databases list
  setAvailableDatabases(databases: Array<{ name: string; description: string }>) {
    this.availableDatabases = databases
    // If no database selected and databases exist, select first
    if (!this.selectedDatabase && databases.length > 0) {
      this.setSelectedDatabase(databases[0].name)
      return
    }

    // If selected database not in available list, fall back to first
    if (this.selectedDatabase) {
      const existsInAvailable = databases.some(db => db.name === this.selectedDatabase)
      if (!existsInAvailable && databases.length > 0) {
        this.setSelectedDatabase(databases[0].name)
      }
    }
  }

  // Restore selected database from localStorage
  restoreSelectedDatabase() {
    const saved = localStorage.getItem('selectedDatabase')
    if (saved) {
      // If available databases loaded, validate; otherwise restore and validate later
      if (this.availableDatabases.length > 0) {
        const existsInAvailable = this.availableDatabases.some(db => db.name === saved)
        if (existsInAvailable) {
          this.selectedDatabase = saved
        } else if (this.availableDatabases.length > 0) {
          this.setSelectedDatabase(this.availableDatabases[0].name)
        }
      } else {
        this.selectedDatabase = saved
      }
    }
  }

  // Fetch databases list
  async loadDatabases() {
    this.databasesLoading = true
    try {
      const response = await fetch(`${SERVER_URL}/databases`)
      if (response.ok) {
        const databases = await response.json()
        this.setAvailableDatabases(databases)
        return databases
      }
    } catch (error) {
      console.error('Failed to load database list:', error)
    } finally {
      this.databasesLoading = false
    }
    return []
  }
}

export const storeGlobalUser = new GlobalUser()
