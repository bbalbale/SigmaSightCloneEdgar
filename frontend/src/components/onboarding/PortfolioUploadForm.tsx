'use client'

import { useState, useRef } from 'react'
import { Upload, FileText, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { onboardingService } from '@/services/onboardingService'

interface PortfolioUploadFormProps {
  onUpload: (portfolioName: string, equityBalance: number, file: File) => void
  disabled?: boolean
  error?: string | null
  onRetry?: () => void
}

export function PortfolioUploadForm({ onUpload, disabled, error, onRetry }: PortfolioUploadFormProps) {
  const [portfolioName, setPortfolioName] = useState('')
  const [equityBalance, setEquityBalance] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      if (!file.name.endsWith('.csv')) {
        setErrors({ ...errors, file: 'Please select a CSV file' })
        setSelectedFile(null)
        return
      }

      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        setErrors({ ...errors, file: 'File size must be less than 10MB' })
        setSelectedFile(null)
        return
      }

      setSelectedFile(file)
      if (errors.file) {
        setErrors({ ...errors, file: '' })
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) {
      // Simulate file input change
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(file)
      if (fileInputRef.current) {
        fileInputRef.current.files = dataTransfer.files
        handleFileSelect({ target: fileInputRef.current } as any)
      }
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!portfolioName.trim()) {
      newErrors.portfolioName = 'Portfolio name is required'
    }

    if (!equityBalance.trim()) {
      newErrors.equityBalance = 'Equity balance is required'
    } else {
      // Strip $ and commas, parse number
      const cleanValue = equityBalance.replace(/[$,]/g, '')
      const numValue = parseFloat(cleanValue)
      if (isNaN(numValue) || numValue <= 0) {
        newErrors.equityBalance = 'Please enter a valid amount'
      }
    }

    if (!selectedFile) {
      newErrors.file = 'Please select a CSV file'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm() || !selectedFile) {
      return
    }

    // Strip $ and commas from equity balance before sending
    const cleanBalance = equityBalance.replace(/[$,]/g, '')
    const numBalance = parseFloat(cleanBalance)

    onUpload(portfolioName, numBalance, selectedFile)
  }

  const handleDownloadTemplate = () => {
    onboardingService.downloadTemplate()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Upload Your Portfolio</h1>
          <p className="text-muted-foreground">
            Let's get your positions loaded into SigmaSight so we can start analyzing your portfolio risk
          </p>
        </div>

        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Portfolio Details</CardTitle>
            <CardDescription>
              Enter your portfolio information and upload your positions CSV
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6">
              {/* Portfolio Name */}
              <div className="space-y-2">
                <label htmlFor="portfolio_name" className="text-sm font-medium">
                  Portfolio Name
                </label>
                <Input
                  id="portfolio_name"
                  type="text"
                  placeholder="My Investment Portfolio"
                  value={portfolioName}
                  onChange={(e) => {
                    setPortfolioName(e.target.value)
                    if (errors.portfolioName) {
                      setErrors({ ...errors, portfolioName: '' })
                    }
                  }}
                  disabled={disabled}
                  className={errors.portfolioName ? 'border-red-500' : ''}
                />
                {errors.portfolioName && (
                  <p className="text-sm text-red-600">{errors.portfolioName}</p>
                )}
              </div>

              {/* Equity Balance */}
              <div className="space-y-2">
                <label htmlFor="equity_balance" className="text-sm font-medium">
                  Equity Balance
                </label>
                <Input
                  id="equity_balance"
                  type="text"
                  placeholder="$100,000"
                  value={equityBalance}
                  onChange={(e) => {
                    setEquityBalance(e.target.value)
                    if (errors.equityBalance) {
                      setErrors({ ...errors, equityBalance: '' })
                    }
                  }}
                  disabled={disabled}
                  className={errors.equityBalance ? 'border-red-500' : ''}
                />
                {errors.equityBalance && (
                  <p className="text-sm text-red-600">{errors.equityBalance}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Your account value minus any margin debt. Calculate as: Total Account Value - Margin Loans. If you don't use margin, this is just your total account value.
                </p>
              </div>

              {/* File Upload */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Positions CSV File
                </label>

                <div
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    selectedFile
                      ? 'border-green-500 bg-green-50 dark:bg-green-950'
                      : errors.file
                      ? 'border-red-500 bg-red-50 dark:bg-red-950'
                      : 'border-gray-300 hover:border-blue-400 bg-gray-50 dark:bg-gray-900'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileSelect}
                    disabled={disabled}
                    className="hidden"
                  />

                  {selectedFile ? (
                    <div className="space-y-2">
                      <FileText className="h-12 w-12 mx-auto text-green-600" />
                      <p className="font-medium">{selectedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(selectedFile.size / 1024).toFixed(2)} KB
                      </p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={disabled}
                      >
                        Choose Different File
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                      <div>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={disabled}
                        >
                          Choose CSV File
                        </Button>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        or drag and drop your file here
                      </p>
                    </div>
                  )}
                </div>

                {errors.file && (
                  <p className="text-sm text-red-600">{errors.file}</p>
                )}

                <div className="flex items-center justify-center pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleDownloadTemplate}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download CSV Template
                  </Button>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
                  {onRetry && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={onRetry}
                      className="mt-3 w-full"
                    >
                      Try Again
                    </Button>
                  )}
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={disabled}
              >
                Upload Portfolio →
              </Button>
            </CardContent>
          </form>
        </Card>
      </div>
    </div>
  )
}
