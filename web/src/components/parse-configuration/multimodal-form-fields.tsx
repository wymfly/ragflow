import { FormLayout } from '@/constants/form';
import { DocumentParserType } from '@/constants/knowledge';
import { useTranslate } from '@/hooks/common-hooks';
import { useMemo } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { SliderInputFormField } from '../slider-input-form-field';
import { FormContainer } from '../form-container';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '../ui/form';
import { RAGFlowSelect } from '../ui/select';
import { Switch } from '../ui/switch';

const excludedParseMethods = [
  DocumentParserType.Table,
  DocumentParserType.Resume,
  DocumentParserType.Picture,
  DocumentParserType.KnowledgeGraph,
  DocumentParserType.Qa,
  DocumentParserType.Tag,
];

export const showMultimodalItems = (
  parserId: DocumentParserType | undefined,
) => {
  return !excludedParseMethods.some((x) => x === parserId);
};

type MultimodalFormFieldsProps = {
  className?: string;
};

const MultimodalFormFields = ({
  className = 'p-10',
}: MultimodalFormFieldsProps) => {
  const { t } = useTranslate('knowledgeConfiguration');
  const form = useFormContext();
  const useMultimodal = useWatch({
    control: form.control,
    name: 'parser_config.multimodal_enhance.use_multimodal',
  });

  const parserOptions = useMemo(() => {
    return [{ value: 'mineru', label: 'MinerU' }];
  }, []);

  return (
    <FormContainer className={className}>
      <FormField
        control={form.control}
        name="parser_config.multimodal_enhance.use_multimodal"
        render={({ field }) => (
          <FormItem className=" items-center space-y-0 ">
            <div className="flex items-center">
              <FormLabel
                tooltip={t('useMultimodalTip')}
                className="text-sm whitespace-nowrap w-1/4"
              >
                {t('useMultimodal')}
              </FormLabel>
              <div className="w-3/4">
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  ></Switch>
                </FormControl>
              </div>
            </div>
            <div className="flex pt-1">
              <div className="w-1/4"></div>
              <FormMessage />
            </div>
          </FormItem>
        )}
      />
      {useMultimodal && (
        <div className="space-y-3">
          <FormField
            control={form.control}
            name="parser_config.multimodal_enhance.parser"
            render={({ field }) => (
              <FormItem className=" items-center space-y-0 ">
                <div className="flex items-center">
                  <FormLabel
                    tooltip={t('multimodalParserTip')}
                    className="text-sm whitespace-nowrap w-1/4"
                  >
                    {t('multimodalParser')}
                  </FormLabel>
                  <div className="w-3/4">
                    <FormControl>
                      <RAGFlowSelect
                        {...field}
                        options={parserOptions}
                      ></RAGFlowSelect>
                    </FormControl>
                  </div>
                </div>
                <div className="flex pt-1">
                  <div className="w-1/4"></div>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="parser_config.multimodal_enhance.enable_image"
            render={({ field }) => (
              <FormItem className=" items-center space-y-0 ">
                <div className="flex items-center">
                  <FormLabel
                    tooltip={t('enableImageTip')}
                    className="text-sm whitespace-nowrap w-1/4"
                  >
                    {t('enableImage')}
                  </FormLabel>
                  <div className="w-3/4">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      ></Switch>
                    </FormControl>
                  </div>
                </div>
                <div className="flex pt-1">
                  <div className="w-1/4"></div>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="parser_config.multimodal_enhance.enable_table"
            render={({ field }) => (
              <FormItem className=" items-center space-y-0 ">
                <div className="flex items-center">
                  <FormLabel
                    tooltip={t('enableTableTip')}
                    className="text-sm whitespace-nowrap w-1/4"
                  >
                    {t('enableTable')}
                  </FormLabel>
                  <div className="w-3/4">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      ></Switch>
                    </FormControl>
                  </div>
                </div>
                <div className="flex pt-1">
                  <div className="w-1/4"></div>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="parser_config.multimodal_enhance.enable_equation"
            render={({ field }) => (
              <FormItem className=" items-center space-y-0 ">
                <div className="flex items-center">
                  <FormLabel
                    tooltip={t('enableEquationTip')}
                    className="text-sm whitespace-nowrap w-1/4"
                  >
                    {t('enableEquation')}
                  </FormLabel>
                  <div className="w-3/4">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      ></Switch>
                    </FormControl>
                  </div>
                </div>
                <div className="flex pt-1">
                  <div className="w-1/4"></div>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          <SliderInputFormField
            name={'parser_config.multimodal_enhance.context_window'}
            label={t('contextWindow')}
            tooltip={t('contextWindowTip')}
            max={5}
            min={0}
            step={1}
            layout={FormLayout.Horizontal}
          ></SliderInputFormField>

          <SliderInputFormField
            name={'parser_config.multimodal_enhance.retrieval_weight'}
            label={t('retrievalWeight')}
            tooltip={t('retrievalWeightTip')}
            max={1}
            min={0}
            step={0.1}
            layout={FormLayout.Horizontal}
          ></SliderInputFormField>
        </div>
      )}
    </FormContainer>
  );
};

export default MultimodalFormFields;
