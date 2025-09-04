import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, File, Image, FileText, FileSpreadsheet, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

const FileUpload = ({ onFilesSelected, maxFiles = 10, maxSizePerFile = 50 * 1024 * 1024 }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const fileInputRef = useRef(null);

  // Types de fichiers supportés
  const supportedTypes = {
    'application/pdf': { icon: FileText, label: 'PDF', color: 'text-red-500' },
    'image/jpeg': { icon: Image, label: 'JPEG', color: 'text-blue-500' },
    'image/jpg': { icon: Image, label: 'JPG', color: 'text-blue-500' },
    'image/png': { icon: Image, label: 'PNG', color: 'text-green-500' },
    'text/csv': { icon: FileSpreadsheet, label: 'CSV', color: 'text-emerald-500' },
    'application/vnd.ms-excel': { icon: FileSpreadsheet, label: 'Excel', color: 'text-emerald-600' },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: FileSpreadsheet, label: 'Excel', color: 'text-emerald-600' }
  };

  const validateFile = (file) => {
    const errors = [];
    
    // Vérifier le type
    if (!supportedTypes[file.type]) {
      errors.push('Type de fichier non supporté');
    }
    
    // Vérifier la taille
    if (file.size > maxSizePerFile) {
      errors.push(`Fichier trop volumineux (max ${Math.round(maxSizePerFile / 1024 / 1024)}MB)`);
    }
    
    return errors;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFiles = useCallback((files) => {
    const fileArray = Array.from(files);
    
    // Vérifier le nombre total de fichiers
    if (selectedFiles.length + fileArray.length > maxFiles) {
      alert(`Vous ne pouvez sélectionner que ${maxFiles} fichiers maximum`);
      return;
    }

    const newFiles = fileArray.map(file => {
      const errors = validateFile(file);
      return {
        file,
        id: Date.now() + Math.random(),
        name: file.name,
        size: file.size,
        type: file.type,
        errors,
        status: errors.length > 0 ? 'error' : 'ready'
      };
    });

    setSelectedFiles(prev => [...prev, ...newFiles]);
  }, [selectedFiles.length, maxFiles]);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (fileId) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[fileId];
      return newProgress;
    });
  };

  const clearAllFiles = () => {
    setSelectedFiles([]);
    setUploadProgress({});
  };

  const uploadFiles = async () => {
    const validFiles = selectedFiles.filter(f => f.status === 'ready');
    
    if (validFiles.length === 0) {
      alert('Aucun fichier valide à uploader');
      return;
    }

    // Notifier le parent des fichiers sélectionnés
    if (onFilesSelected) {
      onFilesSelected(validFiles.map(f => f.file));
    }

    // Simuler l'upload avec progression
    for (const fileData of validFiles) {
      setUploadProgress(prev => ({ ...prev, [fileData.id]: 0 }));
      
      // Simulation de progression
      for (let progress = 0; progress <= 100; progress += 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setUploadProgress(prev => ({ ...prev, [fileData.id]: progress }));
      }
      
      // Marquer comme terminé
      setSelectedFiles(prev => 
        prev.map(f => 
          f.id === fileData.id 
            ? { ...f, status: 'uploaded' }
            : f
        )
      );
    }
  };

  const getFileIcon = (type) => {
    const fileType = supportedTypes[type];
    if (fileType) {
      const IconComponent = fileType.icon;
      return <IconComponent className={`w-5 h-5 ${fileType.color}`} />;
    }
    return <File className="w-5 h-5 text-gray-500" />;
  };

  const getStatusIcon = (file) => {
    const progress = uploadProgress[file.id];
    
    if (file.status === 'error') {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    } else if (file.status === 'uploaded') {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    } else if (progress !== undefined && progress < 100) {
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    }
    
    return null;
  };

  return (
    <div className="w-full">
      {/* Zone de drag & drop */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
          ${dragActive 
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.csv,.xls,.xlsx"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="space-y-2">
          <Upload className="mx-auto h-12 w-12 text-gray-400" />
          <div className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Glissez-déposez vos fichiers ici
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            ou cliquez pour sélectionner des fichiers
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            PDF, Images (JPG, PNG), CSV, Excel • Max {Math.round(maxSizePerFile / 1024 / 1024)}MB par fichier • {maxFiles} fichiers max
          </div>
        </div>
      </div>

      {/* Liste des fichiers sélectionnés */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Fichiers sélectionnés ({selectedFiles.length})
            </h3>
            <button
              onClick={clearAllFiles}
              className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Tout supprimer
            </button>
          </div>
          
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {selectedFiles.map((fileData) => {
              const progress = uploadProgress[fileData.id];
              
              return (
                <div
                  key={fileData.id}
                  className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  {/* Icône du fichier */}
                  <div className="flex-shrink-0">
                    {getFileIcon(fileData.type)}
                  </div>
                  
                  {/* Informations du fichier */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {fileData.name}
                      </p>
                      {getStatusIcon(fileData)}
                    </div>
                    
                    <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{formatFileSize(fileData.size)}</span>
                      {supportedTypes[fileData.type] && (
                        <>
                          <span>•</span>
                          <span>{supportedTypes[fileData.type].label}</span>
                        </>
                      )}
                    </div>
                    
                    {/* Erreurs */}
                    {fileData.errors.length > 0 && (
                      <div className="mt-1">
                        {fileData.errors.map((error, index) => (
                          <p key={index} className="text-xs text-red-500">
                            {error}
                          </p>
                        ))}
                      </div>
                    )}
                    
                    {/* Barre de progression */}
                    {progress !== undefined && progress < 100 && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {progress}% uploadé
                        </p>
                      </div>
                    )}
                  </div>
                  
                  {/* Bouton supprimer */}
                  <button
                    onClick={() => removeFile(fileData.id)}
                    className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
          
          {/* Bouton d'upload */}
          {selectedFiles.some(f => f.status === 'ready') && (
            <div className="pt-2">
              <button
                onClick={uploadFiles}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Uploader {selectedFiles.filter(f => f.status === 'ready').length} fichier(s)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;

