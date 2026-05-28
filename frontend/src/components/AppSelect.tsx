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
    borderColor: state.isFocused ? '#F07820' : '#DCDAD4',
    boxShadow: state.isFocused ? '0 0 0 3px rgba(240, 120, 32, 0.14)' : 'none',
    backgroundColor: '#F7F7F7',
    color: '#1A1918',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'border-color 120ms ease, box-shadow 120ms ease',
    ':hover': {
      borderColor: state.isFocused ? '#F07820' : '#CFCBC2',
    },
  }),
  valueContainer: base => ({
    ...base,
    padding: '0 10px',
  }),
  input: base => ({
    ...base,
    color: '#1A1918',
    margin: 0,
    padding: 0,
  }),
  singleValue: base => ({
    ...base,
    color: '#1A1918',
    fontWeight: 500,
  }),
  multiValue: base => ({
    ...base,
    borderRadius: 999,
    backgroundColor: '#FEF4E8',
  }),
  multiValueLabel: base => ({
    ...base,
    color: '#C5621A',
    fontWeight: 700,
    fontSize: 12,
    paddingLeft: 8,
  }),
  multiValueRemove: base => ({
    ...base,
    color: '#C5621A',
    borderRadius: 999,
    cursor: 'pointer',
    ':hover': {
      backgroundColor: '#FDEBD0',
      color: '#1A1918',
    },
  }),
  placeholder: base => ({
    ...base,
    color: '#888780',
  }),
  indicatorSeparator: () => ({
    display: 'none',
  }),
  dropdownIndicator: (base, state) => ({
    ...base,
    color: state.isFocused ? '#F07820' : '#5F5E5A',
    padding: '0 8px',
    cursor: 'pointer',
    ':hover': { color: '#F07820' },
  }),
  clearIndicator: base => ({
    ...base,
    color: '#888780',
    padding: '0 6px',
    ':hover': { color: '#1A1918' },
  }),
  menu: base => ({
    ...base,
    borderRadius: 8,
    border: '1px solid #E8E6E0',
    boxShadow: '0 12px 28px rgba(26, 25, 24, 0.10)',
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
    color: '#1A1918',
    backgroundColor: state.isSelected
      ? '#FEF4E8'
      : state.isFocused
        ? '#F5F4F1'
        : '#F7F7F7',
    fontSize: 13,
    fontWeight: state.isSelected ? 700 : 500,
    cursor: 'pointer',
    ':active': {
      backgroundColor: '#FEF4E8',
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
