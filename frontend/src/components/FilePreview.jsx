import React, { useState } from 'react';
import { 
  File, FileText, Image, FileSpreadsheet, Download, Eye, 
  CheckCircle, AlertCircle, Clock, Loader2, X 
} from 'lucide-react';

const FilePreview = ({ file, onRemove, showRemoveButton = false, extractedData = null, processingStatus = 'pending' }) => {
  const [showDetails, setShowDetails] = useState(false);

  // Types de fichiers avec leurs icônes et couleurs
  const fileTypeConfig = {
    'application/pdf': { 
      icon: FileText, 
      color: 'text-red-500', 
      bgColor: 'bg-red-50 dark:bg-red-950/20',
      borderColor: 'border-red-200 dark:border-red-800',
      label: 'PDF' 
    },
    'image/jpeg': { 
      icon: Image, 
      color: 'text-blue-500', 
      bgColor: 'bg-blue-50 dark:bg-blue-950/20',
      borderColor: 'border-blue-200 dark:border-blue-800',
      label: 'JPEG' 
    },
    'image/jpg': { 
      icon: Image, 
      color: 'text-blue-500', 
      bgColor: 'bg-blue-50 dark:bg-blue-950/20',
      borderColor: 'border-blue-200 dark:border-blue-800',
      label: 'JPG' 
    },
    'image/png': { 
      icon: Image, 
      color: 'text-green-500', 
      bgColor: 'bg-green-50 dark:bg-green-950/20',
      borderColor: 'border-green-200 dark:border-green-800',
      label: 'PNG' 
    },
    'text/csv': { 
      icon: FileSpreadsheet, 
      color: 'text-emerald-500', 
      bgColor: 'bg-emerald-50 dark:bg-emerald-950/20',
      borderColor: 'border-emerald-200 dark:border-emerald-800',
      label: 'CSV' 
    },
    'application/vnd.ms-excel': { 
      icon: FileSpreadsheet, 
      color: 'text-emerald-600', 
      bgColor: 'bg-emerald-50 dark:bg-emerald-950/20',
      borderColor: 'border-emerald-200 dark:border-emerald-800',
      label: 'Excel' 
    },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { 
      icon: FileSpreadsheet, 
      color: 'text-emerald-600', 
      bgColor: 'bg-emerald-50 dark:bg-emerald-950/20',
      borderColor: 'border-emerald-200 dark:border-emerald-800',
      label: 'Excel' 
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getStatusIcon = () => {
    switch (processingStatus) {
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (processingStatus) {
      case 'processing':
        return 'Traitement en cours...';
      case 'completed':
        return 'Traitement terminé';
      case 'failed':
        return 'Échec du traitement';
      default:
        return 'En attente';
    }
  };

  const config = fileTypeConfig[file.type] || {
    icon: File,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-800',
    borderColor: 'border-gray-200 dark:border-gray-600',
    label: 'Fichier'
  };

  const IconComponent = config.icon;

  return (
    <div className={`border rounded-lg p-3 ${config.bgColor} ${config.borderColor} transition-all duration-200`}>
      <div className="flex items-start space-x-3">
        {/* Icône du fichier */}
        <div className="flex-shrink-0">
          <IconComponent className={`w-8 h-8 ${config.color}`} />
        </div>

        {/* Informations du fichier */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {file.name}
            </h4>
            
            <div className="flex items-center space-x-2">
              {/* Statut de traitement */}
              <div className="flex items-center space-x-1">
                {getStatusIcon()}
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {getStatusText()}
                </span>
              </div>

              {/* Bouton de suppression */}
              {showRemoveButton && onRemove && (
                <button
                  onClick={() => onRemove(file.id)}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  title="Supprimer le fichier"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Métadonnées du fichier */}
          <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
            <span>{config.label}</span>
            <span>•</span>
            <span>{formatFileSize(file.size)}</span>
            {extractedData?.confidence_score && (
              <>
                <span>•</span>
                <span className={`font-medium ${
                  extractedData.confidence_score >= 80 ? 'text-green-600' :
                  extractedData.confidence_score >= 60 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  Confiance: {extractedData.confidence_score}%
                </span>
              </>
            )}
          </div>

          {/* Données extraites - Aperçu */}
          {extractedData && processingStatus === 'completed' && (
            <div className="mt-2">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                {showDetails ? 'Masquer les détails' : 'Voir les données extraites'}
              </button>

              {showDetails && (
                <div className="mt-2 p-2 bg-white dark:bg-gray-700 rounded border text-xs">
                  {/* Données de facture */}
                  {extractedData.invoice_data && (
                    <div className="space-y-1">
                      <div className="font-medium text-gray-900 dark:text-gray-100">Facture détectée:</div>
                      {extractedData.invoice_data.invoice_number && (
                        <div>N°: {extractedData.invoice_data.invoice_number}</div>
                      )}
                      {extractedData.invoice_data.client_name && (
                        <div>Client: {extractedData.invoice_data.client_name}</div>
                      )}
                      {extractedData.invoice_data.total_ttc && (
                        <div>Total: {extractedData.invoice_data.total_ttc}€</div>
                      )}
                    </div>
                  )}

                  {/* Données clients */}
                  {extractedData.clients_data && (
                    <div className="space-y-1">
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        Clients détectés: {extractedData.clients_data.total_count}
                      </div>
                      {extractedData.clients_data.clients?.slice(0, 3).map((client, index) => (
                        <div key={index}>
                          {client.name} {client.email && `(${client.email})`}
                        </div>
                      ))}
                      {extractedData.clients_data.total_count > 3 && (
                        <div className="text-gray-500">
                          ... et {extractedData.clients_data.total_count - 3} autres
                        </div>
                      )}
                    </div>
                  )}

                  {/* Données produits */}
                  {extractedData.products_data && (
                    <div className="space-y-1">
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        Produits détectés: {extractedData.products_data.total_count}
                      </div>
                      {extractedData.products_data.products?.slice(0, 3).map((product, index) => (
                        <div key={index}>
                          {product.name} {product.price && `(${product.price}€)`}
                        </div>
                      ))}
                      {extractedData.products_data.total_count > 3 && (
                        <div className="text-gray-500">
                          ... et {extractedData.products_data.total_count - 3} autres
                        </div>
                      )}
                    </div>
                  )}

                  {/* Texte générique */}
                  {!extractedData.invoice_data && !extractedData.clients_data && !extractedData.products_data && extractedData.extracted_text && (
                    <div className="space-y-1">
                      <div className="font-medium text-gray-900 dark:text-gray-100">Texte extrait:</div>
                      <div className="text-gray-600 dark:text-gray-300">
                        {extractedData.extracted_text.substring(0, 100)}
                        {extractedData.extracted_text.length > 100 && '...'}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Message d'erreur */}
          {processingStatus === 'failed' && (
            <div className="mt-2 text-xs text-red-600 dark:text-red-400">
              Impossible de traiter ce fichier. Vérifiez le format et la qualité.
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
        <div className="flex space-x-2">
          {/* Bouton de prévisualisation (pour les images) */}
          {file.type.startsWith('image/') && (
            <button className="flex items-center space-x-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
              <Eye className="w-3 h-3" />
              <span>Aperçu</span>
            </button>
          )}

          {/* Bouton de téléchargement */}
          <button className="flex items-center space-x-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
            <Download className="w-3 h-3" />
            <span>Télécharger</span>
          </button>
        </div>

        {/* Indicateur de type de données détectées */}
        {extractedData && processingStatus === 'completed' && (
          <div className="text-xs">
            {extractedData.invoice_data && (
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                Facture
              </span>
            )}
            {extractedData.clients_data && (
              <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">
                Clients
              </span>
            )}
            {extractedData.products_data && (
              <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded">
                Produits
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FilePreview;

