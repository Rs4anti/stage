const customModdle = {
  name: 'custom',
  uri: 'http://example.com/custom',
  prefix: 'custom',
  xml: {
    tagAlias: 'lowerCase'
  },
  types: [
    {
      name: 'AtomicExtension',
      superClass: ['Element'],
      properties: [
        {
          name: 'atomicType',
          isAttr: false,
          type: 'String'
        },
        {
          name: 'inputParams',
          isAttr: false,
          type: 'String'
        },
        {
          name: 'outputParams',
          isAttr: false,
          type: 'String'
        },
        {
          name: 'method',
          isAttr: false,
          type: 'String'
        },
        {
          name: 'url',
          isAttr: false,
          type: 'String'
        }
      ]
    },
    {
  name: 'GroupExtension',
  superClass: ['Element'],
  properties: [
    { name: 'groupType', type: 'String' },
    { name: 'name', type: 'String' },
    { name: 'description', type: 'String' },
    { name: 'workflowType', type: 'String' },
    { name: 'members', type: 'String' }, // CSV o JSON stringificato
    { name: 'actors', type: 'String' },  // CSV o JSON stringificato
    { name: 'gdprMap', type: 'String' }  // JSON stringificato
  ]
} 
  ]
};
