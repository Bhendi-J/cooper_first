import { useState, useRef, useCallback } from 'react';
import { receiptApi, ReceiptScanResult } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Camera, Upload, Loader2, Check, X, Receipt } from 'lucide-react';

interface ReceiptScannerProps {
  onScanComplete?: (result: ReceiptScanResult) => void;
  onCancel?: () => void;
}

export function ReceiptScanner({ onScanComplete, onCancel }: ReceiptScannerProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ReceiptScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((selectedFile: File) => {
    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please select a valid image file (PNG, JPG, GIF, or WebP)');
      return;
    }

    // Validate file size (max 10MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }

    setError(null);
    setFile(selectedFile);
    setResult(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(selectedFile);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleScan = async () => {
    if (!file) return;

    setScanning(true);
    setError(null);

    try {
      const scanResult = await receiptApi.scanReceipt(file);
      
      if (scanResult.error) {
        setError(scanResult.error);
      } else {
        setResult(scanResult);
      }
    } catch (err: any) {
      console.error('Scan failed:', err);
      setError(err.response?.data?.error || 'Failed to scan receipt. Please try again.');
    } finally {
      setScanning(false);
    }
  };

  const handleUseResult = () => {
    if (result && onScanComplete) {
      onScanComplete(result);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Receipt className="h-5 w-5 text-blue-500" />
          <CardTitle>Scan Receipt</CardTitle>
        </div>
        <CardDescription>
          Upload a receipt photo and we'll extract the details automatically
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Upload Area */}
        {!preview && (
          <div
            className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const selectedFile = e.target.files?.[0];
                if (selectedFile) handleFileSelect(selectedFile);
              }}
            />
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 rounded-full bg-blue-100 dark:bg-blue-900/30">
                <Upload className="h-8 w-8 text-blue-500" />
              </div>
              <div>
                <p className="font-medium">Drop your receipt here</p>
                <p className="text-sm text-muted-foreground">or click to browse</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Supports PNG, JPG, GIF, WebP (max 10MB)
              </p>
            </div>
          </div>
        )}

        {/* Preview */}
        {preview && !result && (
          <div className="space-y-4">
            <div className="relative aspect-[3/4] max-h-[400px] rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800">
              <img
                src={preview}
                alt="Receipt preview"
                className="w-full h-full object-contain"
              />
              <Button
                variant="secondary"
                size="sm"
                className="absolute top-2 right-2"
                onClick={handleReset}
              >
                <X className="h-4 w-4 mr-1" />
                Remove
              </Button>
            </div>
            <Button 
              className="w-full" 
              onClick={handleScan}
              disabled={scanning}
            >
              {scanning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Camera className="h-4 w-4 mr-2" />
                  Scan Receipt
                </>
              )}
            </Button>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="space-y-4">
            <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-4">
              <div className="flex items-center gap-2 text-green-600 mb-3">
                <Check className="h-5 w-5" />
                <span className="font-medium">Receipt scanned successfully!</span>
              </div>
              
              <div className="space-y-3">
                {result.amount && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Amount</span>
                    <span className="font-semibold">
                      {result.currency === 'INR' ? '₹' : result.currency || ''}{result.amount.toLocaleString()}
                    </span>
                  </div>
                )}
                
                {result.merchant && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Merchant</span>
                    <span>{result.merchant}</span>
                  </div>
                )}
                
                {result.description && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Description</span>
                    <span>{result.description}</span>
                  </div>
                )}
                
                {result.category && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Category</span>
                    <span className="capitalize">{result.category}</span>
                  </div>
                )}
                
                {result.date && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Date</span>
                    <span>{result.date}</span>
                  </div>
                )}

                {result.items && result.items.length > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-sm text-muted-foreground mb-2">Items</p>
                    <div className="space-y-1">
                      {result.items.slice(0, 5).map((item, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span>{item.name}</span>
                          <span>₹{item.price}</span>
                        </div>
                      ))}
                      {result.items.length > 5 && (
                        <p className="text-xs text-muted-foreground">
                          +{result.items.length - 5} more items
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={handleReset}>
                Scan Another
              </Button>
              <Button className="flex-1" onClick={handleUseResult}>
                Use These Details
              </Button>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 dark:bg-red-950/20 text-red-600 rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        {/* Cancel Button */}
        {onCancel && (
          <Button variant="ghost" className="w-full" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default ReceiptScanner;
