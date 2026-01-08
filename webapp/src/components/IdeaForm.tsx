/**
 * Controlled textarea form for submitting ideas
 * Enforces 1-10 sentences with inline validation and helper text
 */

import { useState, useCallback, type FormEvent, type ChangeEvent } from 'react';
import { Button } from './ui';

export interface IdeaFormProps {
  /**
   * Callback when form is submitted with valid idea
   */
  onSubmit: (idea: string) => void;

  /**
   * Whether the form is currently disabled (e.g., during submission)
   */
  disabled?: boolean;

  /**
   * Initial value for the textarea
   */
  initialValue?: string;

  /**
   * Optional CSS class name
   */
  className?: string;
}

interface ValidationState {
  isValid: boolean;
  error: string | null;
  helperText: string;
}

const MAX_CHARACTERS = 10000;
const MIN_SENTENCES = 1;
const MAX_SENTENCES = 10;

/**
 * Count sentences in text (rough approximation)
 * Counts periods, exclamation marks, and question marks followed by whitespace or end of string
 */
function countSentences(text: string): number {
  if (!text.trim()) return 0;
  // Match sentence-ending punctuation followed by whitespace or end of string
  const sentences = text.match(/[.!?](?:\s|$)/g);
  // If no sentence endings found but text exists, count as 1 sentence
  return sentences ? sentences.length : text.trim() ? 1 : 0;
}

/**
 * Validate idea text according to API requirements
 */
function validateIdea(text: string): ValidationState {
  const trimmed = text.trim();
  const length = text.length;
  const sentences = countSentences(trimmed);

  // Empty check
  if (!trimmed) {
    return {
      isValid: false,
      error: null,
      helperText: `Enter your idea (${MIN_SENTENCES}-${MAX_SENTENCES} sentences, max ${MAX_CHARACTERS.toLocaleString()} characters)`,
    };
  }

  // Length check
  if (length > MAX_CHARACTERS) {
    return {
      isValid: false,
      error: `Idea exceeds maximum length of ${MAX_CHARACTERS.toLocaleString()} characters (current: ${length.toLocaleString()})`,
      helperText: `${length.toLocaleString()} / ${MAX_CHARACTERS.toLocaleString()} characters`,
    };
  }

  // Sentence count check
  if (sentences < MIN_SENTENCES) {
    return {
      isValid: false,
      error: `Idea must contain at least ${MIN_SENTENCES} sentence`,
      helperText: `${sentences} sentence${sentences !== 1 ? 's' : ''} (need ${MIN_SENTENCES}-${MAX_SENTENCES})`,
    };
  }

  if (sentences > MAX_SENTENCES) {
    return {
      isValid: false,
      error: `Idea exceeds maximum of ${MAX_SENTENCES} sentences (current: ${sentences})`,
      helperText: `${sentences} sentences (max ${MAX_SENTENCES})`,
    };
  }

  // Valid
  return {
    isValid: true,
    error: null,
    helperText: `${sentences} sentence${sentences !== 1 ? 's' : ''}, ${length.toLocaleString()} / ${MAX_CHARACTERS.toLocaleString()} characters`,
  };
}

export function IdeaForm({
  onSubmit,
  disabled = false,
  initialValue = '',
  className = '',
}: IdeaFormProps) {
  const [value, setValue] = useState(initialValue);
  const [validation, setValidation] = useState<ValidationState>(() => validateIdea(initialValue));
  const [touched, setTouched] = useState(false);

  const handleChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    setValidation(validateIdea(newValue));
  }, []);

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setTouched(true);

      const currentValidation = validateIdea(value);
      setValidation(currentValidation);

      if (currentValidation.isValid) {
        onSubmit(value.trim());
      }
    },
    [value, onSubmit]
  );

  const handleBlur = useCallback(() => {
    setTouched(true);
  }, []);

  const showError = touched && validation.error;

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 ${className}`} noValidate>
      <div>
        <label htmlFor="idea-input" className="block text-sm font-medium text-gray-700">
          Your Idea
          <span className="ml-1 text-gray-500">(required)</span>
        </label>
        <div className="mt-1">
          <textarea
            id="idea-input"
            name="idea"
            rows={6}
            className={`block w-full rounded-md border px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${
              showError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            } disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500`}
            value={value}
            onChange={handleChange}
            onBlur={handleBlur}
            disabled={disabled}
            placeholder="Describe your idea in 1-10 sentences..."
            aria-describedby="idea-helper-text idea-error-text"
            aria-invalid={showError ? 'true' : 'false'}
            aria-required="true"
          />
        </div>

        {/* Helper text */}
        <p
          id="idea-helper-text"
          className={`mt-2 text-sm ${showError ? 'text-red-600' : 'text-gray-500'}`}
        >
          {validation.helperText}
        </p>

        {/* Error message */}
        {showError && (
          <p
            id="idea-error-text"
            className="mt-1 text-sm text-red-600"
            role="alert"
            aria-live="polite"
          >
            {validation.error}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between">
        <Button
          type="submit"
          disabled={disabled || !validation.isValid}
          aria-label="Submit idea for review"
        >
          {disabled ? 'Submitting...' : 'Start Review'}
        </Button>

        {disabled && (
          <span className="text-sm text-gray-600" aria-live="polite">
            Processing your request...
          </span>
        )}
      </div>
    </form>
  );
}
