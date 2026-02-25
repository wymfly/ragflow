'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { CrossLanguageFormField } from '@/components/cross-language-form-field';
import { FormContainer } from '@/components/form-container';
import {
  MetadataFilter,
  MetadataFilterSchema,
} from '@/components/metadata-filter';
import {
  RerankFormFields,
  initialTopKValue,
  topKSchema,
} from '@/components/rerank';
import {
  SimilaritySliderFormField,
  initialSimilarityThresholdValue,
  initialVectorSimilarityWeightValue,
  similarityThresholdSchema,
  vectorSimilarityWeightSchema,
} from '@/components/similarity-slider';
import { ButtonLoading } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Textarea } from '@/components/ui/textarea';
import { Radio } from '@/components/ui/radio';
import { UseKnowledgeGraphFormField } from '@/components/use-knowledge-graph-item';
import { useTestRetrieval } from '@/hooks/use-knowledge-request';
import { trim } from 'lodash';
import { Send } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';

type TestingFormProps = Pick<
  ReturnType<typeof useTestRetrieval>,
  'loading' | 'refetch' | 'setValues'
>;

export default function TestingForm({
  loading,
  refetch,
  setValues,
}: TestingFormProps) {
  const { t } = useTranslation();
  const { id } = useParams();
  const knowledgeBaseId = id;

  const formSchema = z.object({
    question: z.string().min(1, {
      message: t('knowledgeDetails.testTextPlaceholder'),
    }),
    ...similarityThresholdSchema,
    ...vectorSimilarityWeightSchema,
    ...topKSchema,
    use_kg: z.boolean().optional(),
    retrieval_mode: z.string().optional(),
    kb_ids: z.array(z.string()).optional(),
    ...MetadataFilterSchema,
  });

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      ...initialSimilarityThresholdValue,
      ...initialVectorSimilarityWeightValue,
      ...initialTopKValue,
      use_kg: false,
      retrieval_mode: 'auto',
      kb_ids: [knowledgeBaseId],
    },
  });

  const question = form.watch('question');

  const values = useWatch({ control: form.control });

  useEffect(() => {
    setValues(values as Required<z.infer<typeof formSchema>>);
  }, [setValues, values]);

  function onSubmit() {
    refetch();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormContainer className="p-10">
          <SimilaritySliderFormField
            isTooltipShown={true}
          ></SimilaritySliderFormField>
          <RerankFormFields></RerankFormFields>
          <UseKnowledgeGraphFormField name="use_kg"></UseKnowledgeGraphFormField>
          <FormField
            control={form.control}
            name="retrieval_mode"
            render={({ field }) => (
              <FormItem className="items-center space-y-0">
                <div className="flex items-center">
                  <FormLabel className="text-sm whitespace-nowrap w-1/4">
                    {t('knowledgeDetails.retrievalMode')}
                  </FormLabel>
                  <div className="w-3/4">
                    <FormControl>
                      <Radio.Group
                        value={field.value}
                        onChange={field.onChange}
                      >
                        <div className="flex gap-4 w-full text-text-secondary">
                          <Radio value="auto">
                            {t('knowledgeDetails.modeAuto')}
                          </Radio>
                          <Radio value="standard">
                            {t('knowledgeDetails.modeStandard')}
                          </Radio>
                          <Radio value="multimodal">
                            {t('knowledgeDetails.modeMultimodal')}
                          </Radio>
                        </div>
                      </Radio.Group>
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
          <CrossLanguageFormField
            name={'cross_languages'}
          ></CrossLanguageFormField>
          <MetadataFilter prefix=""></MetadataFilter>
        </FormContainer>
        <FormField
          control={form.control}
          name="question"
          render={({ field }) => (
            <FormItem>
              {/* <FormLabel>{t('knowledgeDetails.testText')}</FormLabel> */}
              <FormControl>
                <Textarea {...field}></Textarea>
              </FormControl>

              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <ButtonLoading
            type="submit"
            disabled={!!!trim(question)}
            loading={loading}
          >
            {/* {!loading && <CirclePlay />} */}
            {t('knowledgeDetails.testingLabel')}
            <Send />
          </ButtonLoading>
        </div>
      </form>
    </Form>
  );
}
