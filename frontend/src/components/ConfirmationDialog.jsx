import React, { useState } from 'react'
import { AlertTriangle, Check, X, Clock } from 'lucide-react'

const ConfirmationDialog = ({ 
  isOpen, 
  operation, 
  onConfirm, 
  onReject, 
  onClose,
  isLoading = false 
}) => {
  if (!isOpen || !operation) return null

  const operationDescriptions = {
    'create_client': 'créer un nouveau client',
    'create_invoice': 'créer une nouvelle facture', 
    'create_product': 'créer un nouveau produit',
    'update_client': 'modifier un client existant',
    'delete_client': 'supprimer un client',
    'delete_invoice': 'supprimer une facture',
    'import_data': 'importer des données'
  }

  const operationDesc = operationDescriptions[operation.operation_type] || 'effectuer cette opération'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center space-x-3 p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Confirmation Requise
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Opération sensible sur vos données Sage
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>Attention :</strong> Vous vous apprêtez à{' '}
              <span className="font-semibold">{operationDesc}</span> dans Sage Business Cloud Accounting.
            </p>
          </div>

          {operation.message && (
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Détails de l'opération :
              </p>
              <div className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 rounded p-3">
                {operation.message.split('\n').map((line, index) => (
                  <div key={index}>{line}</div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-sm text-red-800 dark:text-red-200">
              ⚠️ Cette action va <strong>modifier vos données comptables</strong> et ne peut pas être annulée facilement.
            </p>
          </div>

          {/* Timer */}
          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
            <Clock className="w-4 h-4" />
            <span>Cette demande expire dans 5 minutes</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {
              onReject()
              onClose()
            }}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <X className="w-4 h-4 inline mr-1" />
            Annuler
          </button>
          <button
            onClick={() => {
              onConfirm()
              onClose()
            }}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 flex items-center"
          >
            {isLoading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            ) : (
              <Check className="w-4 h-4 mr-2" />
            )}
            Confirmer l'Opération
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmationDialog