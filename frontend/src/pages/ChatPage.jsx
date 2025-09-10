import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import { Send, Bot, User, FileText, Loader2, Sparkles, Calculator, BarChart3, Users, ShoppingCart, CreditCard, TrendingUp } from 'lucide-react';
import ChatInput from '../components/ChatInput';
import FilePreview from '../components/FilePreview';
import ConfirmationDialog from '../components/ConfirmationDialog';

const ChatPage = () => {
  const { user } = useAuth();
  const { messages, sendMessage, isLoading, pendingConfirmation, confirmOperation } = useChat();
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Actions rapides disponibles
  const quickActions = [
    {
      id: 'create_invoice',
      name: 'Créer une facture',
      description: 'Générer une nouvelle facture client',
      icon: FileText
    },
    {
      id: 'check_balance',
      name: 'Consulter le bilan',
      description: 'Afficher le bilan comptable',
      icon: BarChart3
    },
    {
      id: 'list_clients',
      name: 'Liste des clients',
      description: 'Voir tous les clients',
      icon: Users
    },
    {
      id: 'create_client',
      name: 'Nouveau client',
      description: 'Ajouter un client',
      icon: User
    },
    {
      id: 'financial_report',
      name: 'Rapport financier',
      description: 'Générer un rapport',
      icon: TrendingUp
    },
    {
      id: 'upload_documents',
      name: 'Analyser des documents',
      description: 'Uploader et analyser des fichiers',
      icon: FileText
    }
  ];

  // Suggestions pour commencer
  const suggestions = [
    "Créez un nouveau client pour l'entreprise ABC",
    "Analysez mon bilan comptable du mois dernier",
    "Générez une facture pour 1000€ HT",
    "Importez mes données depuis un fichier CSV",
    "Montrez-moi mes KPIs financiers"
  ];

  const handleSendMessage = async (messageData) => {
    try {
      // Les fichiers sont déjà uploadés par ChatInput, récupérer leurs IDs
      const attachedFileIds = messageData.attachedFiles || [];
      
      console.log('Envoi du message avec fichiers attachés:', attachedFileIds);

      // Construire le message avec les références aux fichiers
      let finalMessage = messageData.text;
      if (attachedFileIds.length > 0) {
        finalMessage += `\n\n[Fichiers analysés: ${attachedFileIds.join(', ')}]`;
        
        // Ajouter informations des fichiers si disponible
        if (messageData.files && messageData.files.length > 0) {
          finalMessage += "\n\nDonnées extraites:";
          messageData.files.forEach(file => {
            finalMessage += `\n- ${file.name}`;
            if (file.analysisSummary?.potential_financial_data) {
              finalMessage += " (💰 Document financier détecté)";
            }
            if (file.isProcessed) {
              finalMessage += " (✓ Analysé avec succès)";
            }
          });
        }
      }

      // Envoyer le message au ChatContext avec les IDs des fichiers
      await sendMessage(finalMessage, null, attachedFileIds);
      
    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
    }
  };

  const handleQuickAction = async (actionId) => {
    const actionMessages = {
      'create_invoice': 'Je voudrais créer une nouvelle facture',
      'check_balance': 'Pouvez-vous me montrer le bilan comptable ?',
      'list_clients': 'Affichez-moi la liste de tous mes clients',
      'create_client': 'Je veux ajouter un nouveau client',
      'financial_report': 'Générez-moi un rapport financier complet',
      'upload_documents': 'Je voudrais analyser des documents comptables'
    };

    const message = actionMessages[actionId];
    if (message) {
      await sendMessage(message);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const handleConfirmOperation = (confirmed) => {
    if (pendingConfirmation) {
      confirmOperation(pendingConfirmation.id, confirmed);
    }
  };

  const formatMessage = (content) => {
    // Remplacer les retours à la ligne par des <br>
    return content.split('\n').map((line, index) => (
      <React.Fragment key={index}>
        {line}
        {index < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* En-tête */}
      <div className="flex-shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Assistant IA Comptable
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Spécialisé en Sage Business Cloud Accounting • Traitement de documents activé
            </p>
          </div>
        </div>
      </div>

      {/* Zone de messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Bienvenue, {user?.username} !
            </h3>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-8">
              Je suis votre assistant IA spécialisé en comptabilité Sage. 
              Vous pouvez me poser des questions, uploader des documents (factures, CSV, Excel) 
              ou me demander d'effectuer des opérations comptables.
            </p>

            {/* Actions rapides */}
            <div className="mb-8">
              <h4 className="text-md font-medium text-gray-900 dark:text-gray-100 mb-4">
                Actions rapides
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
                {quickActions.map((action) => {
                  const IconComponent = action.icon;
                  return (
                    <div
                      key={action.id}
                      onClick={() => handleQuickAction(action.id)}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 cursor-pointer hover:shadow-md transition-shadow"
                    >
                      <IconComponent className="w-8 h-8 text-blue-500 mb-2 mx-auto" />
                      <h5 className="font-medium text-gray-900 dark:text-gray-100 mb-1 text-center">
                        {action.name}
                      </h5>
                      <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                        {action.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Suggestions */}
            <div>
              <h4 className="text-md font-medium text-gray-900 dark:text-gray-100 mb-4">
                Suggestions pour commencer
              </h4>
              <div className="flex flex-wrap gap-2 justify-center max-w-3xl mx-auto">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="inline-flex items-center px-3 py-2 text-sm bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
                  >
                    <Sparkles className="w-3 h-3 mr-1" />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.is_from_user ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex space-x-3 max-w-3xl ${message.is_from_user ? 'flex-row-reverse space-x-reverse' : ''}`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.is_from_user 
                    ? 'bg-blue-600' 
                    : 'bg-gray-600'
                }`}>
                  {message.is_from_user ? (
                    <User className="w-5 h-5 text-white" />
                  ) : (
                    <Bot className="w-5 h-5 text-white" />
                  )}
                </div>

                {/* Message */}
                <div className={`rounded-lg px-4 py-3 ${
                  message.is_from_user
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700'
                }`}>
                  <div className="text-sm">
                    {formatMessage(message.content)}
                  </div>
                  
                  {/* Timestamp */}
                  <div className={`text-xs mt-2 ${
                    message.is_from_user 
                      ? 'text-blue-100' 
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {message.created_at ? new Date(message.created_at).toLocaleTimeString() : ''}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}

        {/* Indicateur de frappe */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex space-x-3 max-w-3xl">
              <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">L'assistant analyse vos documents et prépare sa réponse...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Fichiers uploadés récemment */}
        {uploadedFiles.length > 0 && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Fichiers récemment traités ({uploadedFiles.length})
            </h4>
            <div className="space-y-2">
              {uploadedFiles.slice(-5).map((file) => (
                <FilePreview
                  key={file.id}
                  file={file}
                  extractedData={file.extractedData}
                  processingStatus={file.status}
                  showRemoveButton={true}
                  onRemove={(fileId) => {
                    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
                  }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Zone d'input avec support de fichiers */}
      <div className="flex-shrink-0">
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          onFilesAttached={(files) => {
            console.log('Fichiers attachés:', files);
          }}
        />
      </div>

      {/* Dialogue de confirmation pour les opérations sensibles */}
      <ConfirmationDialog
        isOpen={!!pendingConfirmation}
        operation={pendingConfirmation}
        onConfirm={() => handleConfirmOperation(true)}
        onReject={() => handleConfirmOperation(false)}
        onClose={() => handleConfirmOperation(false)}
        isLoading={isLoading}
      />
    </div>
  );
};

export default ChatPage;

