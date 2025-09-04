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
      files: attachedFiles
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
      // Valider et traiter les fichiers
      const validFiles = [];
      
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

        validFiles.push({
          id: Date.now() + Math.random(),
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          preview: null
        });
      }

      if (validFiles.length > 0) {
        setAttachedFiles(prev => [...prev, ...validFiles]);
        
        // Notifier le parent si nécessaire
        if (onFilesAttached) {
          onFilesAttached(validFiles);
        }
      }
    } catch (error) {
      console.error('Erreur lors de l\'ajout des fichiers:', error);
      alert('Erreur lors de l\'ajout des fichiers');
    } finally {
      setIsUploading(false);
    }
  };

  const removeFile = (fileId) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
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
                className="flex items-center space-x-2 bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                {getFileIcon(fileData.type)}
                <span className="text-gray-900 dark:text-gray-100 truncate max-w-32">
                  {fileData.name}
                </span>
                <span className="text-gray-500 dark:text-gray-400 text-xs">
                  {formatFileSize(fileData.size)}
                </span>
                <button
                  onClick={() => removeFile(fileData.id)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <X className="w-3 h-3" />
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

