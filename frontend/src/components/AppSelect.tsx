import Select, {
  components,
  type MultiValue,
  type OptionProps,
  type SingleValue,
  type StylesConfig,
} from 'react-select'
import { Check } from 'lucide-react'

export interface SelectOption {
  value: string
  label: string
}

const styles: StylesConfig<SelectOption, boolean> = {
  control: (base, state) => ({
    ...base,
    minHeight: 36,
    borderRadius: 8,
    borderColor: state.isFocused
      ? 'var(--theme-brand-600)'
      : 'var(--theme-stone-200)',
    boxShadow: state.isFocused
      ? '0 0 0 3px color-mix(in srgb, var(--theme-brand-600) 16%, transparent)'
      : 'none',
    backgroundColor: 'var(--theme-stone-50)',
    color: 'var(--theme-stone-900)',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'border-color 120ms ease, box-shadow 120ms ease',
    ':hover': {
      borderColor: state.isFocused
        ? 'var(--theme-brand-600)'
        : 'var(--theme-stone-300)',
    },
  }),
  valueContainer: base => ({
    ...base,
    padding: '0 10px',
  }),
  input: base => ({
    ...base,
    color: 'var(--theme-stone-900)',
    margin: 0,
    padding: 0,
  }),
  singleValue: base => ({
    ...base,
    color: 'var(--theme-stone-900)',
    fontWeight: 500,
  }),
  multiValue: base => ({
    ...base,
    borderRadius: 999,
    backgroundColor: 'var(--theme-brand-50)',
  }),
  multiValueLabel: base => ({
    ...base,
    color: 'var(--theme-brand-700)',
    fontWeight: 700,
    fontSize: 12,
    paddingLeft: 8,
  }),
  multiValueRemove: base => ({
    ...base,
    color: 'var(--theme-brand-700)',
    borderRadius: 999,
    cursor: 'pointer',
    ':hover': {
      backgroundColor: 'var(--theme-brand-100)',
      color: 'var(--theme-stone-900)',
    },
  }),
  placeholder: base => ({
    ...base,
    color: 'var(--theme-stone-400)',
  }),
  indicatorSeparator: () => ({
    display: 'none',
  }),
  dropdownIndicator: (base, state) => ({
    ...base,
    color: state.isFocused
      ? 'var(--theme-brand-600)'
      : 'var(--theme-stone-500)',
    padding: '0 8px',
    cursor: 'pointer',
    ':hover': { color: 'var(--theme-brand-600)' },
  }),
  clearIndicator: base => ({
    ...base,
    color: 'var(--theme-stone-400)',
    padding: '0 6px',
    ':hover': { color: 'var(--theme-stone-900)' },
  }),
  menu: base => ({
    ...base,
    borderRadius: 8,
    border: '1px solid var(--theme-stone-200)',
    boxShadow: '0 12px 28px color-mix(in srgb, var(--theme-stone-950) 16%, transparent)',
    backgroundColor: 'var(--theme-card)',
    overflow: 'hidden',
    zIndex: 80,
  }),
  menuPortal: base => ({
    ...base,
    zIndex: 9999,
  }),
  menuList: base => ({
    ...base,
    padding: 4,
  }),
  option: (base, state) => ({
    ...base,
    borderRadius: 6,
    color: state.isSelected
      ? 'var(--theme-brand-700)'
      : 'var(--theme-stone-900)',
    backgroundColor: state.isSelected
      ? 'var(--theme-brand-50)'
      : state.isFocused
        ? 'var(--theme-stone-100)'
        : 'var(--theme-card)',
    fontSize: 13,
    fontWeight: state.isSelected ? 700 : 500,
    cursor: 'pointer',
    ':active': {
      backgroundColor: 'var(--theme-brand-50)',
    },
  }),
}

function CheckboxOption(props: OptionProps<SelectOption, true>) {
  return (
    <components.Option {...props}>
      <div className="flex items-center gap-2">
        <span
          className={[
            'flex size-4 items-center justify-center rounded border transition-colors',
            props.isSelected
              ? 'border-brand-600 bg-brand-600 text-white'
              : 'border-stone-300 bg-white text-transparent',
          ].join(' ')}
        >
          <Check className="size-3" strokeWidth={2.4} />
        </span>
        <span className="min-w-0 truncate">{props.label}</span>
      </div>
    </components.Option>
  )
}

export function AppSelect({
  value,
  options,
  onChange,
  placeholder = 'Selecionar',
  className,
  isClearable = false,
}: {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  isClearable?: boolean
}) {
  const selected = options.find(option => option.value === value) ?? null

  function handleChange(option: SingleValue<SelectOption>) {
    onChange(option?.value ?? '')
  }

  return (
    <Select<SelectOption, false>
      value={selected}
      options={options}
      onChange={handleChange}
      placeholder={placeholder}
      styles={styles as StylesConfig<SelectOption, false>}
      className={className}
      classNamePrefix="saltim-select"
      isSearchable
      isClearable={isClearable}
      menuPortalTarget={typeof document !== 'undefined' ? document.body : undefined}
      menuPosition="fixed"
    />
  )
}

export function AppMultiSelect({
  value,
  options,
  onChange,
  placeholder = 'Selecionar',
  className,
}: {
  value: string[]
  options: SelectOption[]
  onChange: (value: string[]) => void
  placeholder?: string
  className?: string
}) {
  const selected = options.filter(option => value.includes(option.value))

  function handleChange(optionsValue: MultiValue<SelectOption>) {
    onChange(optionsValue.map(option => option.value))
  }

  return (
    <Select<SelectOption, true>
      value={selected}
      options={options}
      onChange={handleChange}
      placeholder={placeholder}
      styles={styles as StylesConfig<SelectOption, true>}
      className={className}
      classNamePrefix="saltim-select"
      isSearchable
      isMulti
      closeMenuOnSelect={false}
      hideSelectedOptions={false}
      menuPortalTarget={typeof document !== 'undefined' ? document.body : undefined}
      menuPosition="fixed"
      components={{ Option: CheckboxOption }}
    />
  )
}

export const AppCheckboxMultiSelect = AppMultiSelect
