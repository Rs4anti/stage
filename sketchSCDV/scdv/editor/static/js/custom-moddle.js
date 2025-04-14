// custom-moddle.js
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
    }
  ]
};
