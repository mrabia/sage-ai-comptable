import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, X, File, Image, FileText, FileSpreadsheet } from 'lucide-react';

const ChatInput = ({ onSendMessage, onFilesAttached, disabled = false }) => {
  const [message, setMessage] = useState('');
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Types de fichiers supportés avec leurs icônes
  const fileTypeIcons = {
    'application/pdf': { icon: FileText, color: 'text-red-500', label: 'PDF' },
    'image/jpeg': { icon: Image, color: 'text-blue-500', label: 'JPG' },
    'image/jpg': { icon: Image, color: 'text-blue-500', label: 'JPG' },
    'image/png': { icon: Image, color: 'text-green-500', label: 'PNG' },
    'text/csv': { icon: FileSpreadsheet, color: 'text-emerald-500', label: 'CSV' },
    'application/vnd.ms-excel': { icon: FileSpreadsheet, color: 'text-emerald-600', label: 'Excel' },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: FileSpreadsheet, color: 'text-emerald-600', label: 'Excel' }
  };

  // Auto-resize du textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [message]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if ((!message.trim() && attachedFiles.length === 0) || disabled || isUploading) {
      return;
    }

    const messageData = {
      text: message.trim(),
      files: attachedFiles,
      attachedFiles: attachedFiles.map(f => f.file_id || f.id).filter(Boolean) // IDs pour le backend
    };

    // Réinitialiser l'input
    setMessage('');
    setAttachedFiles([]);

    // Envoyer le message
    if (onSendMessage) {
      await onSendMessage(messageData);
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFilesAdded(files);
    // Réinitialiser l'input file
    e.target.value = '';
  };

  const handleFilesAdded = async (files) => {
    if (files.length === 0) return;

    setIsUploading(true);

    try {
      // Valider et uploader les fichiers vers le backend
      const uploadedFiles = [];
      
      for (const file of files) {
        // Vérifier le type de fichier
        if (!fileTypeIcons[file.type]) {
          alert(`Type de fichier non supporté: ${file.name}`);
          continue;
        }

        // Vérifier la taille (50MB max)
        if (file.size > 50 * 1024 * 1024) {
          alert(`Fichier trop volumineux: ${file.name} (max 50MB)`);
          continue;
        }

        // Upload le fichier vers le backend
        try {
          const formData = new FormData();
          formData.append('file', file);
          
          // Récupérer le token d'authentification
          const token = localStorage.getItem('token');
          if (!token) {
            alert('Vous devez être connecté pour uploader des fichiers');
            continue;
          }

          const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || '/api'}/files/upload`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`
            },
            body: formData
          });

          if (response.ok) {
            const uploadResult = await response.json();
            
            uploadedFiles.push({
              id: uploadResult.file_id,           // VRAI ID de la base de données
              file_id: uploadResult.file_id,      // ID pour le backend
              file,                               // Objet File original pour l'affichage
              name: uploadResult.filename,
              size: uploadResult.file_size,
              type: uploadResult.file_type,
              isProcessed: uploadResult.is_processed,
              analysisStatus: uploadResult.is_processed ? 'success' : 'error',
              processingError: uploadResult.processing_error,
              analysisSummary: uploadResult.analysis_summary
            });
          } else {
            const errorData = await response.json();
            alert(`Erreur lors de l'upload de ${file.name}: ${errorData.error}`);
            continue;
          }
        } catch (uploadError) {
          console.error('Erreur lors de l\'upload:', uploadError);
          alert(`Erreur lors de l'upload de ${file.name}`);
          continue;
        }
      }

      if (uploadedFiles.length > 0) {
        setAttachedFiles(prev => [...prev, ...uploadedFiles]);
        
        // Notifier le parent avec les vrais IDs
        if (onFilesAttached) {
          onFilesAttached(uploadedFiles);
        }
      }
    } catch (error) {
      console.error('Erreur lors de l\'ajout des fichiers:', error);
      alert('Erreur lors de l\'ajout des fichiers');
    } finally {
      setIsUploading(false);
    }
  };

  const removeFile = async (fileId) => {
    try {
      // Supprimer le fichier côté backend si c'est un vrai ID
      const fileToRemove = attachedFiles.find(f => f.id === fileId);
      if (fileToRemove && fileToRemove.file_id) {
        const token = localStorage.getItem('token');
        if (token) {
          try {
            await fetch(`${import.meta.env.VITE_API_BASE_URL || '/api'}/files/${fileToRemove.file_id}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
          } catch (deleteError) {
            console.warn('Erreur lors de la suppression backend:', deleteError);
            // Continue avec la suppression frontend même si le backend échoue
          }
        }
      }
      
      // Supprimer le fichier de l'état frontend
      setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      // Continuer avec la suppression frontend en cas d'erreur
      setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileIcon = (type) => {
    const fileType = fileTypeIcons[type];
    if (fileType) {
      const IconComponent = fileType.icon;
      return <IconComponent className={`w-4 h-4 ${fileType.color}`} />;
    }
    return <File className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      {/* Fichiers attachés */}
      {attachedFiles.length > 0 && (
        <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-2">
            {attachedFiles.map((fileData) => (
              <div
                key={fileData.id}
                className={`flex items-center space-x-2 rounded-lg px-3 py-2 text-sm ${
                  fileData.analysisStatus === 'success' 
                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
                    : fileData.analysisStatus === 'error' 
                    ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                    : 'bg-gray-100 dark:bg-gray-700'
                }`}
              >
                {getFileIcon(fileData.type)}
                <div className="flex-1 min-w-0">
                  <div className="text-gray-900 dark:text-gray-100 truncate max-w-32">
                    {fileData.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                    <span>{formatFileSize(fileData.size)}</span>
                    {fileData.isProcessed ? (
                      <span className="text-green-600 dark:text-green-400 flex items-center">
                        ✓ Analysé
                        {fileData.analysisSummary?.potential_financial_data && (
                          <span className="ml-1">💰</span>
                        )}
                      </span>
                    ) : fileData.analysisStatus === 'error' ? (
                      <span className="text-red-600 dark:text-red-400" title={fileData.processingError}>
                        ⚠ Erreur
                      </span>
                    ) : (
                      <span className="text-gray-500 dark:text-gray-400">
                        📊 En cours...
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => removeFile(fileData.id)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex-shrink-0"
                  title="Supprimer le fichier"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zone d'input */}
      <div className="p-4">
        <div className="flex items-end space-x-2">
          {/* Bouton d'attachement */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            className="flex-shrink-0 p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Attacher des fichiers"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* Input file caché */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.csv,.xls,.xlsx"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Zone de texte */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={attachedFiles.length > 0 ? "Décrivez ce que vous voulez faire avec ces fichiers..." : "Tapez votre message..."}
              disabled={disabled}
              className="w-full resize-none border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-12 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              rows="1"
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
          </div>

          {/* Bouton d'envoi */}
          <button
            onClick={handleSend}
            disabled={(!message.trim() && attachedFiles.length === 0) || disabled || isUploading}
            className="flex-shrink-0 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Envoyer le message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>

        {/* Indicateur de chargement */}
        {isUploading && (
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Traitement des fichiers...
          </div>
        )}

        {/* Aide contextuelle */}
        {attachedFiles.length > 0 && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            💡 L'IA va analyser vos fichiers et peut automatiquement extraire les données pour les intégrer dans Sage
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInput;

